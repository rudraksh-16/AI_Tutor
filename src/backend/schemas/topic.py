from pydantic import BaseModel, UUID4, Field
from typing import List, Optional
from datetime import datetime
from src.backend.enums.status import TopicStatus
from src.backend.schemas.chapter import ChapterRead


class TopicBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    user_summary: str = Field(..., min_length=1, max_length=5000)


class TopicCreate(TopicBase):
    user_id: UUID4


class TopicRead(TopicBase):
    id: UUID4
    user_id: UUID4
    status: TopicStatus
    curriculum_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    chapters: List[ChapterRead] = []

    class Config:
        from_attributes = True
