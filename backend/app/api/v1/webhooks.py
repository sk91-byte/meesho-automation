import hashlib
import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

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
async def verify_instagram_webhook(request: Request):
    """Meta Webhook Challenge Verification."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    logger.info(f"Webhook verification request: mode={mode}, token={token}, challenge={challenge}")
    
    if mode == "subscribe" and token == settings.INSTAGRAM_VERIFY_TOKEN:
        logger.info("Meta Webhook verified successfully!")
        return Response(content=str(challenge or ""), media_type="text/plain", status_code=200)
    
    logger.warning(f"Meta Webhook verification failed. Expected token '{settings.INSTAGRAM_VERIFY_TOKEN}', got '{token}'")
    return Response(content="Verification failed", status_code=403)


@router.post("/instagram")
async def receive_instagram_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Meta Webhook Engine:
    Handles both Direct Messages (messages) and Post Comments (comments).
    """
    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256")
    
    if not verify_webhook_signature(raw_body, signature_header):
        logger.error("Invalid Meta Webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    
    background_tasks.add_task(async_process_webhook_payload, payload, payload_hash)

    return {"status": "received", "idempotency_hash": payload_hash}


async def async_process_webhook_payload(payload: Dict[str, Any], payload_hash: str):
    """Async Background Worker for Messages & Comment-to-DM Automation."""
    async with AsyncSessionLocal() as db:
        try:
            entry_list = payload.get("entry", [])
            for entry in entry_list:
                event_id = str(entry.get("id", payload_hash))
                
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

                # 1. Handle Direct Messaging Events
                messaging_events = entry.get("messaging", [])
                for messaging in messaging_events:
                    sender_id = messaging.get("sender", {}).get("id")
                    message_data = messaging.get("message", {})
                    message_text = message_data.get("text")

                    if sender_id and message_text:
                        await _process_inbound_message(db, sender_id, message_text, message_data.get("mid"))

                # 2. Handle Post Comment Events (Comment-to-DM Automation)
                changes_events = entry.get("changes", [])
                for change in changes_events:
                    field = change.get("field")
                    value = change.get("value", {})
                    if field == "comments":
                        comment_id = value.get("id")
                        media_id = value.get("media", {}).get("id")
                        comment_text = value.get("text", "")
                        from_user = value.get("from", {})
                        from_user_id = from_user.get("id")

                        if from_user_id and comment_text:
                            await _process_inbound_comment(db, comment_id, media_id, from_user_id, comment_text)

                webhook_event.processing_status = WebhookStatusEnum.PROCESSED
                await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error processing background webhook event: {e}", exc_info=True)


async def _process_inbound_comment(db: AsyncSession, comment_id: str, media_id: str, from_user_id: str, comment_text: str):
    """
    Comment-to-DM Automation Flow:
    1. Customer comments on post.
    2. Bot replies on post: 'Check your DMs for price & details! 📩'
    3. Bot sends DM to commenter with full product details (Price, Colors, Sizes, COD, Order Instructions).
    """
    logger.info(f"Processing comment {comment_id} on media {media_id} from user {from_user_id}")

    # Find matching product with variants eagerly loaded
    prod_stmt = select(Product).options(selectinload(Product.variants)).where(Product.active == True).order_by(Product.created_at.desc())
    prod_res = await db.execute(prod_stmt)
    product = prod_res.scalars().first()

    if not product:
        logger.warning("No active product found for comment automation.")
        return

    colors = [v.value for v in product.variants if v.type == "color" and v.available]
    sizes = [v.value for v in product.variants if v.type == "size" and v.available]
    
    color_str = ", ".join(colors) if colors else "Standard Colors"
    size_str = ", ".join(sizes) if sizes else "Standard Sizes"

    dm_text = (
        f"Hi! 👋 Thanks for commenting on {product.product_name}!\n\n"
        f"Here are the complete product details:\n"
        f"• Selling Price: ₹{int(product.selling_price)}\n"
        f"• Available Colors: {color_str}\n"
        f"• Available Sizes: {size_str}\n"
        f"• Delivery: {product.delivery_information}\n"
        f"• COD: {'Available' if product.cod_available else 'Not Available'}\n"
        f"• Return Policy: {product.return_policy}\n\n"
        f"Please follow our page for updates! 🌸\n"
        f"Reply to this DM with your preferred color and quantity to place an order!"
    )

    cust_res = await db.execute(select(Customer).where(Customer.instagram_user_id == from_user_id))
    customer = cust_res.scalars().first()
    if not customer:
        customer = Customer(instagram_user_id=from_user_id)
        db.add(customer)
        await db.flush()

    conv_res = await db.execute(select(Conversation).where(Conversation.customer_id == customer.customer_id))
    conversation = conv_res.scalars().first()
    if not conversation:
        conversation = Conversation(customer_id=customer.customer_id)
        db.add(conversation)
        await db.flush()

    db.add(Message(
        conversation_id=conversation.conversation_id,
        sender_type=SenderTypeEnum.CUSTOMER,
        message_text=f"[Commented on Post]: {comment_text}"
    ))

    db.add(Message(
        conversation_id=conversation.conversation_id,
        sender_type=SenderTypeEnum.AI,
        message_text=dm_text,
        ai_generated=True,
        intent="COMMENT_TO_DM"
    ))
    await db.commit()


async def _process_inbound_message(db: AsyncSession, sender_id: str, message_text: str, mid: str):
    """Internal Direct Message processing workflow."""
    result = await db.execute(select(Customer).where(Customer.instagram_user_id == sender_id))
    customer = result.scalars().first()
    if not customer:
        customer = Customer(instagram_user_id=sender_id)
        db.add(customer)
        await db.flush()

    conv_result = await db.execute(select(Conversation).where(Conversation.customer_id == customer.customer_id))
    conversation = conv_result.scalars().first()
    if not conversation:
        conversation = Conversation(customer_id=customer.customer_id)
        db.add(conversation)
        await db.flush()

    c_msg = Message(
        conversation_id=conversation.conversation_id,
        instagram_message_id=mid,
        sender_type=SenderTypeEnum.CUSTOMER,
        sender_instagram_id=sender_id,
        message_text=message_text
    )
    db.add(c_msg)

    if conversation.human_mode_active:
        logger.info(f"Human mode active for conversation {conversation.conversation_id}. AI auto-reply paused.")
        await db.commit()
        return

    history = []
    interpretation = await ai_provider.interpret_message(message_text, history)
    
    conversation.current_intent = interpretation.intent
    conversation.language = interpretation.language

    if interpretation.requires_human:
        conversation.requires_human_review = True
        conversation.human_review_reason = interpretation.human_reason or "AI confidence threshold / complex request"
        await db.commit()
        return

    prod_result = await db.execute(select(Product).options(selectinload(Product.variants)).where(Product.active == True).order_by(Product.created_at.desc()))
    product = prod_result.scalars().first()
    
    tool_results = {}
    if product:
        await MultiProductContextService.set_active_product_context(db, conversation.conversation_id, product.product_id)
        
        tool_results["product_name"] = product.product_name
        tool_results["price"] = product.selling_price
        tool_results["actual_cost"] = product.actual_price

        if interpretation.requested_variant:
            requested = interpretation.requested_variant.lower()
            matching_variants = [v for v in product.variants if v.value.lower() == requested]
            if matching_variants:
                tool_results["variant_available"] = matching_variants[0].available
                tool_results["variant"] = matching_variants[0].value
            else:
                tool_results["variant_available"] = False
                tool_results["variant"] = interpretation.requested_variant
                cust_req = CustomerRequest(
                    customer_id=customer.customer_id,
                    conversation_id=conversation.conversation_id,
                    product_id=product.product_id,
                    request_type=RequestTypeEnum.VARIANT,
                    requested_value=interpretation.requested_variant,
                    original_message=message_text
                )
                db.add(cust_req)

    bot_reply = ""
    if interpretation.intent == "PLACE_ORDER":
        draft = await OrderDraftService.get_or_create_draft(db, conversation.conversation_id, product.product_id if product else None)
        await OrderDraftService.update_draft_with_revision(db, draft, interpretation.order_fields_detected)
        
        if not (customer.name and customer.phone and customer.house_building and customer.road_area_colony):
            bot_reply = "Please share your delivery details (Name, Mobile Number, House/Building No., Area/Colony) 😊"
        else:
            bot_reply = OrderDraftService.generate_final_order_review_message(draft, product)
    else:
        bot_reply = await ai_provider.generate_verified_response(message_text, interpretation, tool_results, history)

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
