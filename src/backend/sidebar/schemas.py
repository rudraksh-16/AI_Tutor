from pydantic import BaseModel, UUID4
from typing import List
from src.backend.enums.status import TopicStatus


class SidebarTopicItem(BaseModel):
    id: UUID4
    title: str
    status: TopicStatus

    class Config:
        from_attributes = True


class SidebarResponse(BaseModel):
    in_progress: List[SidebarTopicItem]
    completed: List[SidebarTopicItem]
