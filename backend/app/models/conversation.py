import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class SenderTypeEnum(str, Enum):
    CUSTOMER = "CUSTOMER"
    AI = "AI"
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    instagram_account_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    current_intent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    language: Mapped[str] = mapped_column(String(50), default="hinglish", nullable=False)
    missing_fields: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    human_review_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    human_mode_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    messages: Mapped[List["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    product_mentions: Mapped[List["ConversationProductMention"]] = relationship("ConversationProductMention", back_populates="conversation", cascade="all, delete-orphan")
    drafts: Mapped[List["OrderDraft"]] = relationship("OrderDraft", back_populates="conversation", cascade="all, delete-orphan")


class ConversationProductMention(Base):
    """Tracks multi-product context across a single conversation (§3 & §4)."""
    __tablename__ = "conversation_product_mentions"

    mention_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    is_current_active_context: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    mentioned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="product_mentions")


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False, index=True)
    instagram_message_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    sender_type: Mapped[SenderTypeEnum] = mapped_column(SQLEnum(SenderTypeEnum), nullable=False)
    sender_instagram_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tool_calls: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    response_validation_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
