import logging
from typing import List, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.common.exceptions import EntityNotFoundError, ValidationError
from src.backend.enums.status import ChapterStatus, TopicStatus
from src.backend.models.chapter import Chapter
from src.backend.models.chapter_plan import ChapterPlan
from src.backend.chapters.repository import chapter_repo
from src.backend.models.topic import Topic

logger = logging.getLogger(__name__)

class CourseRepository:
    """Handles composite course data operations to break circular service dependencies."""

    @classmethod
    async def update_status(cls, db: AsyncSession, chapter_id: UUID, action: str) -> str:
        """Centralized status management for chapters and parent topics."""
        chapter, plan = await cls._get_chapter_and_plan(db, chapter_id)
        topic = await cls._get_topic(db, chapter.topic_id)

        if action == "start":
            cls._transition_to_start(chapter, topic)
        elif action == "quiz_pending":
            cls._transition_to_quiz_pending(chapter, plan)
        elif action == "complete":
            await cls._transition_to_complete(db, chapter, plan)
        else:
            raise ValidationError(f"Invalid status action: {action}")

        await db.commit()
        return f"{action} chapter: {plan.title}"

    @classmethod
    async def get_curriculum_context(cls, db: AsyncSession, chapter_id: UUID) -> Dict[str, Any]:
        """Fetch the full curriculum context (topic + all chapters) for a chapter."""
        chapter_res = await db.execute(select(Chapter).filter(Chapter.id == chapter_id))
        ref_chapter = chapter_res.scalars().first()
        if not ref_chapter: 
            raise EntityNotFoundError(f"Chapter not found: {chapter_id}")

        topic = await cls._get_topic(db, ref_chapter.topic_id)
        
        chap_q = select(Chapter).filter(Chapter.topic_id == topic.id).order_by(Chapter.order_index)
        chapters_res = await db.execute(chap_q)
        chapters = chapters_res.scalars().all()

        return {
            "topic": topic.title,
            "user_summary": topic.user_summary,
            "chapters": [
                {"chapter_number": c.order_index, "chapter_title": c.title, "chapter_description": c.description}
                for c in chapters
            ]
        }

    @staticmethod
    async def get_chapter_outline(db: AsyncSession, chapter_id: UUID) -> Dict[str, Any]:
        """Fetch the specific outline (ChapterPlan items) for a chapter."""
        query = (
            select(Chapter.title.label("chapter_title"), ChapterPlan.title.label("outline_title"),
                   ChapterPlan.order_index, ChapterPlan.is_completed)
            .join(ChapterPlan, ChapterPlan.chapter_id == Chapter.id)
            .filter(Chapter.id == chapter_id)
            .order_by(ChapterPlan.order_index)
        )
        res = await db.execute(query)
        data = res.all()
        if not data: 
            raise EntityNotFoundError(f"No chapters/plan found for chapter_id: {chapter_id}")

        return {
            "status": "success",
            "chapter": data[0].chapter_title,
            "outline": [
                {"outline_title": o.outline_title, "order_index": o.order_index, "is_completed": o.is_completed}
                for o in data
            ]
        }

    @staticmethod
    async def get_chapter_full_plan(db: AsyncSession, chapter_id: UUID) -> Dict[str, Any]:
        """Fetch the title and full textual content for a chapter's teaching plan."""
        query = (
            select(ChapterPlan.content, ChapterPlan.title)
            .filter(ChapterPlan.chapter_id == chapter_id)
            .limit(1)
        )
        res = await db.execute(query)
        row = res.first()
        if not row:
            raise EntityNotFoundError(f"No plan found for chapter_id: {chapter_id}")
        
        return {
            "title": row.title,
            "content": row.content,
        }

    @staticmethod
    async def _get_chapter_and_plan(db: AsyncSession, chapter_id: UUID) -> Tuple[Chapter, ChapterPlan]:
        plan_res = await db.execute(select(ChapterPlan).filter(ChapterPlan.chapter_id == chapter_id).limit(1))
        plan = plan_res.scalars().first()
        if not plan: 
            raise EntityNotFoundError(f"Chapter Plan not found for chapter: {chapter_id}")
        
        chap_res = await db.execute(select(Chapter).filter(Chapter.id == plan.chapter_id))
        chapter = chap_res.scalars().first()
        return chapter, plan

    @staticmethod
    async def _get_topic(db: AsyncSession, topic_id: UUID) -> Topic:
        topic_res = await db.execute(select(Topic).filter(Topic.id == topic_id))
        topic = topic_res.scalars().first()
        if not topic: 
            raise EntityNotFoundError(f"Topic not found: {topic_id}")
        return topic

    @staticmethod
    def _transition_to_start(chapter: Chapter, topic: Topic) -> None:
        if chapter.status in (ChapterStatus.PENDING, ChapterStatus.LOCKED):
            chapter.status = ChapterStatus.IN_PROGRESS
        if topic.status == TopicStatus.PENDING:
            topic.status = TopicStatus.IN_PROGRESS

    @staticmethod
    def _transition_to_quiz_pending(chapter: Chapter, plan: ChapterPlan) -> None:
        plan.is_completed = True
        chapter.status = ChapterStatus.QUIZ_PENDING

    @staticmethod
    async def _transition_to_complete(db: AsyncSession, chapter: Chapter, plan: ChapterPlan) -> None:
        plan.is_completed = True
        chapter.status = ChapterStatus.COMPLETED
        # Unlock next chapter to PENDING
        next_chapter = await chapter_repo.get_next_chapter(
            db, chapter.topic_id, chapter.order_index
        )
        if next_chapter:
            next_chapter.status = ChapterStatus.PENDING

course_repo = CourseRepository()
