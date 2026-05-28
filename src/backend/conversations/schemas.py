from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional, List
from datetime import datetime


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    topic_id: Optional[UUID] = None
    chapter_id: Optional[UUID] = None
    type: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConversationWithMessages(ConversationRead):
    messages: List["MessageRead"] = []


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversation_id: UUID
    role: str
    content: Optional[str] = None
    sequence: int
    meta: Optional[dict] = None
    created_at: datetime


# Resolve forward reference
ConversationWithMessages.model_rebuild()
