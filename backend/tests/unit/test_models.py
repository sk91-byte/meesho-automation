import pytest
from app.models.user import User, RoleEnum
from app.models.product import Product, ProductVariant, ProductFAQ
from app.models.customer import Customer, CustomerRequest, RequestTypeEnum
from app.models.order import Order, OrderItem, OrderStateEnum


def test_user_model_creation():
    user = User(
        email="test@meesho.store",
        hashed_password="hashed_pass_value",
        full_name="Test User",
        role=RoleEnum.OWNER
    )
    assert user.email == "test@meesho.store"
    assert user.role == RoleEnum.OWNER
    assert user.is_active is True


def test_product_model_and_variants():
    product = Product(
        sku="SKU-BAG-001",
        product_name="Women's Sling Bag",
        actual_price=299.0,
        selling_price=449.0,
        description="Premium PU Leather Bag"
    )
    assert product.sku == "SKU-BAG-001"
    assert product.actual_price == 299.0
    assert product.selling_price == 449.0
    assert product.currency == "INR"


def test_order_pricing_snapshot_integrity():
    order = Order(
        customer_id="cust_123",
        order_state=OrderStateEnum.CONFIRMED,
        customer_name="Rahul",
        total_selling_price=898.0,
        total_actual_cost=598.0,
        expected_margin=300.0
    )
    item = OrderItem(
        product_id="prod_123",
        product_name="Women's Sling Bag",
        actual_price=299.0,
        selling_price=449.0,
        quantity=2
    )
    assert order.total_selling_price == 898.0
    assert item.actual_price == 299.0
    assert item.selling_price == 449.0
    assert item.quantity == 2
