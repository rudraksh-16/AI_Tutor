import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.enums.status import TopicStatus, ChapterStatus
from src.backend.models.chapter import Chapter
from src.backend.models.topic import Topic
from src.backend.topics.repository import topic_repo

logger = logging.getLogger(__name__)

class CurriculumRepository:
    """Handles composite data operations for curricula to break circular service dependencies."""

    @classmethod
    async def upsert_curriculum_item(
        cls, 
        db: AsyncSession, 
        user_id: UUID, 
        topic_id: UUID, 
        topic_title: str,
        chapter_number: int,
        chapter_title: str,
        chapter_outline: str,
        user_summary: str
    ) -> None:
        """Composite logic for saving or updating curriculum components."""
        topic = await cls.ensure_topic(db, user_id, topic_id, topic_title, user_summary)
        await cls.upsert_chapter(db, topic.id, chapter_number, chapter_title, chapter_outline)
        await db.commit()

    @staticmethod
    async def get_curriculum_data(db: AsyncSession, topic_id: UUID) -> Dict[str, Any]:
        """Fetch full curriculum structure for a topic."""
        topic = await topic_repo.get(db, topic_id)
        if not topic:
            return {}

        chapters_res = await db.execute(
            select(Chapter).filter(Chapter.topic_id == topic_id).order_by(Chapter.order_index)
        )
        chapters = chapters_res.scalars().all()

        return {
            "topic": topic.title,
            "user_summary": topic.user_summary,
            "chapters": [
                {
                    "chapter_number": c.order_index,
                    "chapter_title": c.title,
                    "chapter_description": c.description,
                }
                for c in chapters
            ]
        }

    @staticmethod
    async def ensure_topic(db: AsyncSession, user_id: UUID, topic_id: UUID, title: str, summary: str) -> Topic:
        res = await db.execute(select(Topic).filter(Topic.user_id == user_id, Topic.id == topic_id))
        topic = res.scalars().first()
        if not topic:
            topic = Topic(id=topic_id, user_id=user_id, title=title, 
                          status=TopicStatus.PENDING.value, user_summary=summary)
            db.add(topic)
        else:
            topic.user_summary = summary
        return topic

    @staticmethod
    async def upsert_chapter(db: AsyncSession, topic_id: UUID, number: int, title: str, outline: str) -> None:
        res = await db.execute(select(Chapter).filter(Chapter.topic_id == topic_id, Chapter.order_index == number))
        chapter = res.scalars().first()
        if chapter:
            chapter.title = title
            chapter.description = outline
        else:
            db.add(Chapter(topic_id=topic_id, title=title, order_index=number, 
                           status=ChapterStatus.LOCKED.value, description=outline))

curriculum_repo = CurriculumRepository()
