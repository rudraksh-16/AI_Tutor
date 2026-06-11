from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.utils import get_current_user
from src.backend.common.exceptions import EntityNotFoundError
from src.backend.db.database import get_db
from src.backend.models.conversation import ConversationType
from src.backend.models.user import User
from src.backend.conversations.repository import conversation_repo
from src.backend.conversations.message_repository import message_repo
from src.backend.conversations.schemas import ConversationRead, ConversationWithMessages, MessageRead

router = APIRouter()


@router.get("/", response_model=List[ConversationRead])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ConversationRead]:
    """List all conversations for the current user."""
    conversations = await conversation_repo.get_by_user(db, current_user.id)
    return conversations


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationWithMessages:
    """Get a conversation with its full message history."""
    conv = await conversation_repo.get_with_messages(db, conversation_id)
    if not conv:
        raise EntityNotFoundError(f"Conversation not found: {conversation_id}")
    
    if str(conv.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return conv


@router.get("/{conversation_id}/messages", response_model=List[MessageRead])
async def get_messages(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MessageRead]:
    """Get all messages for a conversation."""
    conv = await conversation_repo.get(db, conversation_id)
    if not conv:
        raise EntityNotFoundError(f"Conversation not found: {conversation_id}")
    
    if str(conv.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    messages = await message_repo.get_by_conversation(db, conversation_id)
    return messages


@router.get("/topic/{topic_id}/messages", response_model=List[MessageRead])
async def get_topic_messages(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MessageRead]:
    """Get all messages for a topic's curriculum conversation."""
    conv = await conversation_repo.get_or_create_by_topic(db, current_user.id, topic_id)
    messages = await message_repo.get_by_conversation(db, conv.id)
    return messages


@router.get("/chapter/{chapter_id}/messages", response_model=List[MessageRead])
async def get_chapter_messages(
    chapter_id: UUID,
    type: str,  # "teacher" or "quiz"
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MessageRead]:
    """Get all messages for a chapter conversation (teacher or quiz)."""
    conv_type = ConversationType.TEACHER if type == "teacher" else ConversationType.QUIZ
    conv = await conversation_repo.get_or_create_by_chapter(
        db, current_user.id, chapter_id, conv_type
    )
    messages = await message_repo.get_by_conversation(db, conv.id)
    return messages
