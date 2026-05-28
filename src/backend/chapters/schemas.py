from pydantic import BaseModel, UUID4
from datetime import datetime
from src.backend.enums.status import ChapterStatus
from typing import Optional


class ChapterBase(BaseModel):
    title: str
    order_index: int
    status: ChapterStatus
    description: str


class ChapterRead(ChapterBase):
    id: UUID4
    topic_id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChapterUpdate(BaseModel):
    status: ChapterStatus
