from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.models.topic import Topic
from src.backend.enums.status import TopicStatus
from src.backend.shared.repository import BaseRepository


class TopicRepository(BaseRepository[Topic]):
    def __init__(self):
        super().__init__(Topic)

    async def get_with_chapters(self, db: AsyncSession, id: UUID) -> Optional[Topic]:
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.chapters))
            .filter(self.model.id == id, self.model.deleted_at.is_(None))
        )
        return result.scalars().first()

    async def get_by_user(self, db: AsyncSession, user_id: UUID) -> List[Topic]:
        result = await db.execute(
            select(self.model)
            .filter(self.model.user_id == user_id, self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(self, db: AsyncSession, topic_id: UUID, new_status: TopicStatus) -> Optional[Topic]:
        result = await db.execute(
            select(self.model).filter(self.model.id == topic_id, self.model.deleted_at.is_(None))
        )
        topic = result.scalars().first()
        if topic:
            topic.status = new_status
            await db.commit()
            await db.refresh(topic)
        return topic


topic_repo = TopicRepository()
