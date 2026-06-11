import logging
from typing import List, Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.chapter import Chapter
from src.backend.models.chapter_plan import ChapterPlan
from src.backend.models.topic import Topic

logger = logging.getLogger(__name__)

class PlannerRepository:
    """Handles data operations for the chapter planner to break circular service dependencies."""

    @staticmethod
    async def get_chapters_for_topic(db: AsyncSession, topic_id: str) -> List[Any]:
        """Fetch all chapters for a given topic ID sorted by order index."""
        topic_uuid = UUID(topic_id)
        query = (
            select(
                Chapter.id.label("chapter_id"),
                Chapter.title.label("chapter_title"),
                Chapter.order_index.label("chapter_order_index"),
                Chapter.description,
                Topic.title.label("topic_title"),
                Topic.user_summary.label("user_summary"),
            )
            .join(Topic, Chapter.topic_id == Topic.id)
            .filter(Topic.id == topic_uuid)
            .order_by(Chapter.order_index)
        )
        res = await db.execute(query)
        return list(res.all())

    @staticmethod
    async def plan_exists(db: AsyncSession, chapter_id: UUID) -> bool:
        """Check if a plan already exists for the given chapter."""
        query = select(ChapterPlan).filter(ChapterPlan.chapter_id == chapter_id)
        res = await db.execute(query)
        return res.scalars().first() is not None

    @staticmethod
    async def insert_plan(db: AsyncSession, chapter_id: UUID, plan: str, title: str, index: int) -> None:
        """Persist a new chapter plan to the database."""
        db.add(ChapterPlan(chapter_id=chapter_id, title=title, order_index=index, content=plan))
        await db.commit()
        logger.info("Plan for chapter %s saved successfully.", title)

planner_repo = PlannerRepository()
