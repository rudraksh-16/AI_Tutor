from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.models.chapter import Chapter
from src.backend.enums.status import ChapterStatus
from src.backend.shared.repository import BaseRepository


class ChapterRepository(BaseRepository[Chapter]):
    def __init__(self):
        super().__init__(Chapter)

    async def get_by_topic(self, db: AsyncSession, topic_id: UUID) -> List[Chapter]:
        result = await db.execute(
            select(self.model)
            .filter(self.model.topic_id == topic_id, self.model.deleted_at.is_(None))
            .order_by(self.model.order_index)
        )
        return list(result.scalars().all())

    async def get_next_chapter(self, db: AsyncSession, topic_id: UUID, current_order_index: int) -> Optional[Chapter]:
        result = await db.execute(
            select(self.model)
            .filter(
                self.model.topic_id == topic_id,
                self.model.order_index > current_order_index,
                self.model.deleted_at.is_(None),
            )
            .order_by(self.model.order_index)
            .limit(1)
        )
        return result.scalars().first()

    async def unlock_first_chapter(self, db: AsyncSession, topic_id: UUID) -> Optional[Chapter]:
        """Set the first chapter (by order_index) to PENDING (accessible but not started)."""
        result = await db.execute(
            select(self.model)
            .filter(self.model.topic_id == topic_id, self.model.deleted_at.is_(None))
            .order_by(self.model.order_index)
            .limit(1)
        )
        chapter = result.scalars().first()
        if chapter:
            chapter.status = ChapterStatus.PENDING
            await db.commit()
            await db.refresh(chapter)
        return chapter


chapter_repo = ChapterRepository()
