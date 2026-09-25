import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.order import Order, OrderItem, OrderStateEnum
from app.models.product import Product

logger = logging.getLogger("instagram_reseller")

REQUIRED_ORDER_FIELDS = ["customer_name", "phone", "house_building", "road_area_colony"]


class OrderStateMachine:
    """Conversational Order State Machine."""

    @classmethod
    async def process_order_step(
        cls,
        db: AsyncSession,
        customer: Customer,
        conversation: Conversation,
        product: Optional[Product],
        extracted_fields: Dict[str, Any]
    ) -> Tuple[OrderStateEnum, List[str], Optional[str]]:
        """
        Updates customer order details and determines missing fields & next bot prompt.
        """
        # Update customer details if detected
        if "customer_name" in extracted_fields and extracted_fields["customer_name"]:
            customer.name = extracted_fields["customer_name"]
        if "phone" in extracted_fields and extracted_fields["phone"]:
            customer.phone = extracted_fields["phone"]
        if "house_building" in extracted_fields and extracted_fields["house_building"]:
            customer.house_building = extracted_fields["house_building"]
        if "road_area_colony" in extracted_fields and extracted_fields["road_area_colony"]:
            customer.road_area_colony = extracted_fields["road_area_colony"]

        # Determine missing mandatory fields
        missing = []
        if not customer.name:
            missing.append("customer_name")
        if not customer.phone:
            missing.append("phone")
        if not customer.house_building:
            missing.append("house_building")
        if not customer.road_area_colony:
            missing.append("road_area_colony")

        conversation.missing_fields = missing

        if missing:
            new_state = OrderStateEnum.COLLECTING_DETAILS
            next_field = missing[0]
            prompt = cls._get_field_prompt(next_field)
            return new_state, missing, prompt
        else:
            new_state = OrderStateEnum.READY_FOR_CONFIRMATION
            summary_prompt = cls._generate_confirmation_summary(customer, product)
            return new_state, [], summary_prompt

    @staticmethod
    def _get_field_prompt(field_name: str) -> str:
        prompts = {
            "customer_name": "Great! Please share your full name for the delivery.",
            "phone": "Thanks! Please provide your 10-digit mobile number.",
            "house_building": "Got it. What is your House No. / Flat No. / Building Name?",
            "road_area_colony": "And your Road Name, Area, or Colony?"
        }
        return prompts.get(field_name, "Please provide your delivery details.")

    @staticmethod
    def _generate_confirmation_summary(customer: Customer, product: Optional[Product]) -> str:
        prod_name = product.product_name if product else "Selected Item"
        price = product.selling_price if product else 0.0
        return (
            f"Here is your order summary:\n"
            f"Product: {prod_name}\n"
            f"Selling Price: ₹{int(price)}\n"
            f"Delivery Name: {customer.name}\n"
            f"Phone: {customer.phone}\n"
            f"Address: {customer.house_building}, {customer.road_area_colony}\n\n"
            f"Reply 'CONFIRM' or 'YES' to place your order!"
        )

    @classmethod
    async def create_confirmed_order_transaction(
        cls,
        db: AsyncSession,
        customer: Customer,
        conversation: Conversation,
        product: Product,
        variant_name: Optional[str] = None,
        quantity: int = 1
    ) -> Order:
        """
        Creates confirmed order record with immutable price snapshot.
        """
        selling_price = product.selling_price
        actual_price = product.actual_price
        total_selling = selling_price * quantity
        total_actual = actual_price * quantity
        expected_margin = total_selling - total_actual

        order = Order(
            customer_id=customer.customer_id,
            conversation_id=conversation.conversation_id,
            order_state=OrderStateEnum.CONFIRMED,
            customer_name=customer.name,
            phone=customer.phone,
            house_building=customer.house_building,
            road_area_colony=customer.road_area_colony,
            total_selling_price=total_selling,
            total_actual_cost=total_actual,
            expected_margin=expected_margin,
            payment_method="COD"
        )
        db.add(order)
        await db.flush()  # Obtain order_id

        order_item = OrderItem(
            order_id=order.order_id,
            product_id=product.product_id,
            product_name=product.product_name,
            actual_price=actual_price,
            selling_price=selling_price,
            variant=variant_name or "Standard",
            quantity=quantity
        )
        db.add(order_item)
        
        # Link to conversation
        conversation.order_id = order.order_id
        await db.commit()
        await db.refresh(order)
        return order
