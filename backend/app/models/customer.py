import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class RequestTypeEnum(str, Enum):
    COLOR = "COLOR"
    SIZE = "SIZE"
    VARIANT = "VARIANT"
    BUNDLE = "BUNDLE"
    CUSTOMIZATION = "CUSTOMIZATION"
    PRICE_REQUEST = "PRICE_REQUEST"
    DISCOUNT_REQUEST = "DISCOUNT_REQUEST"
    OTHER = "OTHER"


class RequestStatusEnum(str, Enum):
    PENDING = "PENDING"
    CHECKED = "CHECKED"
    RESOLVED = "RESOLVED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    instagram_user_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    instagram_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    house_building: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    road_area_colony: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    requests: Mapped[List["CustomerRequest"]] = relationship("CustomerRequest", back_populates="customer", cascade="all, delete-orphan")


class CustomerRequest(Base):
    __tablename__ = "customer_requests"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    product_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("products.product_id", ondelete="SET NULL"), nullable=True, index=True)
    request_type: Mapped[RequestTypeEnum] = mapped_column(SQLEnum(RequestTypeEnum), default=RequestTypeEnum.OTHER, nullable=False)
    requested_value: Mapped[str] = mapped_column(String(255), nullable=False)
    original_message: Mapped[Text] = mapped_column(Text, nullable=False)
    status: Mapped[RequestStatusEnum] = mapped_column(SQLEnum(RequestStatusEnum), default=RequestStatusEnum.PENDING, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="requests")
