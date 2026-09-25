from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, RoleEnum
from app.models.conversation import Conversation, Message, SenderTypeEnum

router = APIRouter(prefix="/conversations", tags=["Chat Viewer & Human Handoff"])


class ManualReplyRequest(BaseModel):
    message_text: str


@router.get("/")
async def list_conversations(
    requires_human_only: bool = Query(False, description="Filter human review queue"),
    human_mode_only: bool = Query(False, description="Filter human mode active chats"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Conversation).options(
        selectinload(Conversation.messages)
    )
    if requires_human_only:
        stmt = stmt.where(Conversation.requires_human_review == True)
    if human_mode_only:
        stmt = stmt.where(Conversation.human_mode_active == True)
        
    stmt = stmt.order_by(Conversation.last_activity_at.desc())
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    return conversations


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Conversation).options(
        selectinload(Conversation.messages)
    ).where(Conversation.conversation_id == conversation_id)
    result = await db.execute(stmt)
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/{conversation_id}/takeover")
async def takeover_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.STAFF]))
):
    """Pause AI auto-replies and activate Human Mode for this chat."""
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv.human_mode_active = True
    conv.requires_human_review = False
    await db.commit()
    return {"status": "success", "human_mode_active": True}


@router.post("/{conversation_id}/resume")
async def resume_ai_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.STAFF]))
):
    """Resume AI automation for this chat."""
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv.human_mode_active = False
    conv.requires_human_review = False
    await db.commit()
    return {"status": "success", "human_mode_active": False}


@router.post("/{conversation_id}/reply")
async def send_manual_owner_reply(
    conversation_id: str,
    reply: ManualReplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.STAFF]))
):
    """Owner sends manual message to customer."""
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Store human message
    msg = Message(
        conversation_id=conversation_id,
        sender_type=SenderTypeEnum.HUMAN,
        message_text=reply.message_text
    )
    db.add(msg)
    
    # Ensure human mode is active while owner is manually replying
    conv.human_mode_active = True
    await db.commit()
    return {"status": "sent", "message_text": reply.message_text}
