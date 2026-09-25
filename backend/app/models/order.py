import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlalchemy import String, Float, Integer, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DraftStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    REVIEW_SENT = "REVIEW_SENT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class OrderStateEnum(str, Enum):
    NEW = "NEW"
    INTERESTED = "INTERESTED"
    ORDER_STARTED = "ORDER_STARTED"
    COLLECTING_DETAILS = "COLLECTING_DETAILS"
    READY_FOR_CONFIRMATION = "READY_FOR_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    ORDER_CREATED = "ORDER_CREATED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class OrderDraft(Base):
    """Mutable Order Draft entity (§5 & §6)."""
    __tablename__ = "order_drafts"

    draft_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("products.product_id", ondelete="SET NULL"), nullable=True, index=True)
    variant_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    house_building: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    road_area_colony: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[DraftStatusEnum] = mapped_column(SQLEnum(DraftStatusEnum), default=DraftStatusEnum.DRAFT, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="drafts")
    revisions: Mapped[List["OrderDraftRevision"]] = relationship("OrderDraftRevision", back_populates="draft", cascade="all, delete-orphan")


class OrderDraftRevision(Base):
    """Audit revision history for order drafts (§6)."""
    __tablename__ = "order_draft_revisions"

    revision_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    draft_id: Mapped[str] = mapped_column(String(36), ForeignKey("order_drafts.draft_id", ondelete="CASCADE"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    draft: Mapped["OrderDraft"] = relationship("OrderDraft", back_populates="revisions")


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("conversations.conversation_id", ondelete="SET NULL"), nullable=True, index=True)
    draft_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("order_drafts.draft_id", ondelete="SET NULL"), nullable=True, index=True)
    order_state: Mapped[OrderStateEnum] = mapped_column(SQLEnum(OrderStateEnum), default=OrderStateEnum.NEW, nullable=False, index=True)
    
    # Customer Details Snapshot
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    house_building: Mapped[str] = mapped_column(Text, nullable=False)
    road_area_colony: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Financial Summaries
    total_selling_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_actual_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    expected_margin: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), default="COD", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    item_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.product_id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Immutable Snapshots at time of order creation
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    actual_price: Mapped[float] = mapped_column(Float, nullable=False)  # Meesho cost snapshot
    selling_price: Mapped[float] = mapped_column(Float, nullable=False)  # Selling price snapshot
    variant: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
