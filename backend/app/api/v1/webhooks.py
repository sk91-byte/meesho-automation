import hashlib
import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.instagram import WebhookEvent, WebhookStatusEnum
from app.models.customer import Customer, CustomerRequest, RequestTypeEnum
from app.models.conversation import Conversation, Message, SenderTypeEnum
from app.models.product import Product
from app.services.instagram_service import verify_webhook_signature, MetaInstagramGraphService
from app.services.ai_service import ai_provider
from app.services.draft_service import MultiProductContextService, OrderDraftService

logger = logging.getLogger("instagram_reseller")

router = APIRouter(prefix="/webhooks", tags=["Meta Instagram Webhooks"])


@router.get("/instagram")
async def verify_instagram_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token")
):
    """Meta Webhook Challenge Verification."""
    if hub_mode == "subscribe" and hub_verify_token == settings.INSTAGRAM_VERIFY_TOKEN:
        logger.info("Meta Webhook verified successfully!")
        return Response(content=hub_challenge, media_type="text/plain")
    logger.warning("Meta Webhook verification token mismatch")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/instagram")
async def receive_instagram_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Production Webhook Engine:
    1. Verifies HMAC Signature
    2. Validates Idempotency
    3. Immediately acknowledges Meta with 200 OK (< 200ms)
    4. Offloads processing to Background Task worker (prevents timeout/cancellation during cold starts)
    """
    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256")
    
    # Verify HMAC signature
    if not verify_webhook_signature(raw_body, signature_header):
        logger.error("Invalid Meta Webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    
    # Enqueue background processing task so Meta gets HTTP 200 OK immediately
    background_tasks.add_task(async_process_webhook_payload, payload, payload_hash)

    return {"status": "received", "idempotency_hash": payload_hash}


async def async_process_webhook_payload(payload: Dict[str, Any], payload_hash: str):
    """Async Background Worker Processing Payload safely in background task."""
    async with AsyncSessionLocal() as db:
        try:
            entry_list = payload.get("entry", [])
            for entry in entry_list:
                event_id = str(entry.get("id", payload_hash))
                
                # Check idempotency
                existing_event = await db.get(WebhookEvent, event_id)
                if existing_event:
                    logger.info(f"Webhook event '{event_id}' already processed. Skipping.")
                    continue

                webhook_event = WebhookEvent(
                    event_id=event_id,
                    event_type=payload.get("object", "instagram"),
                    payload_hash=payload_hash,
                    processing_status=WebhookStatusEnum.PENDING
                )
                db.add(webhook_event)
                await db.flush()

                messaging_events = entry.get("messaging", [])
                for messaging in messaging_events:
                    sender_id = messaging.get("sender", {}).get("id")
                    message_data = messaging.get("message", {})
                    message_text = message_data.get("text")

                    if not sender_id or not message_text:
                        continue

                    # Execute full processing
                    await _process_inbound_message(db, sender_id, message_text, message_data.get("mid"))

                webhook_event.processing_status = WebhookStatusEnum.PROCESSED
                await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error processing background webhook event: {e}", exc_info=True)


async def _process_inbound_message(db: AsyncSession, sender_id: str, message_text: str, mid: str):
    """Internal message processing workflow."""
    # Find or create customer
    result = await db.execute(select(Customer).where(Customer.instagram_user_id == sender_id))
    customer = result.scalars().first()
    if not customer:
        customer = Customer(instagram_user_id=sender_id)
        db.add(customer)
        await db.flush()

    # Find or create conversation
    conv_result = await db.execute(select(Conversation).where(Conversation.customer_id == customer.customer_id))
    conversation = conv_result.scalars().first()
    if not conversation:
        conversation = Conversation(customer_id=customer.customer_id)
        db.add(conversation)
        await db.flush()

    # Log customer message
    c_msg = Message(
        conversation_id=conversation.conversation_id,
        instagram_message_id=mid,
        sender_type=SenderTypeEnum.CUSTOMER,
        sender_instagram_id=sender_id,
        message_text=message_text
    )
    db.add(c_msg)

    # Check if owner human mode is active
    if conversation.human_mode_active:
        logger.info(f"Human mode active for conversation {conversation.conversation_id}. AI auto-reply paused.")
        await db.commit()
        return

    # Interpret customer message via Groq AI engine
    history = []
    interpretation = await ai_provider.interpret_message(message_text, history)
    
    conversation.current_intent = interpretation.intent
    conversation.language = interpretation.language

    # Check human handoff trigger
    if interpretation.requires_human:
        conversation.requires_human_review = True
        conversation.human_review_reason = interpretation.human_reason or "AI confidence threshold / complex request"
        await db.commit()
        return

    # Look up product context
    prod_result = await db.execute(select(Product).where(Product.active == True).order_by(Product.created_at.desc()))
    product = prod_result.scalars().first()
    
    tool_results = {}
    if product:
        # Set active product context
        await MultiProductContextService.set_active_product_context(db, conversation.conversation_id, product.product_id)
        
        tool_results["product_name"] = product.product_name
        tool_results["price"] = product.selling_price
        tool_results["actual_cost"] = product.actual_price

        # Check requested variant availability if applicable
        if interpretation.requested_variant:
            requested = interpretation.requested_variant.lower()
            matching_variants = [v for v in product.variants if v.value.lower() == requested]
            if matching_variants:
                tool_results["variant_available"] = matching_variants[0].available
                tool_results["variant"] = matching_variants[0].value
            else:
                tool_results["variant_available"] = False
                tool_results["variant"] = interpretation.requested_variant
                # Record customer request for unavailable variant
                cust_req = CustomerRequest(
                    customer_id=customer.customer_id,
                    conversation_id=conversation.conversation_id,
                    product_id=product.product_id,
                    request_type=RequestTypeEnum.VARIANT,
                    requested_value=interpretation.requested_variant,
                    original_message=message_text
                )
                db.add(cust_req)

    # Handle order draft collection flow
    bot_reply = ""
    if interpretation.intent == "PLACE_ORDER":
        draft = await OrderDraftService.get_or_create_draft(db, conversation.conversation_id, product.product_id if product else None)
        # Update draft with detected fields
        await OrderDraftService.update_draft_with_revision(db, draft, interpretation.order_fields_detected)
        
        # Check missing details
        if not (customer.name and customer.phone and customer.house_building and customer.road_area_colony):
            bot_reply = "Please share your delivery details (Name, Mobile Number, House/Building No., Area/Colony) 😊"
        else:
            bot_reply = OrderDraftService.generate_final_order_review_message(draft, product)
    else:
        bot_reply = await ai_provider.generate_verified_response(message_text, interpretation, tool_results, history)

    # Log AI message
    ai_msg = Message(
        conversation_id=conversation.conversation_id,
        sender_type=SenderTypeEnum.AI,
        message_text=bot_reply,
        ai_generated=True,
        ai_model=settings.GROQ_MODEL,
        intent=interpretation.intent
    )
    db.add(ai_msg)
    await db.commit()
