import asyncio
import logging
from typing import Dict, Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.common.exceptions import EntityNotFoundError
from src.backend.db.database import SessionLocal
from src.backend.enums.status import TopicStatus, ChapterStatus
from src.backend.models.chapter import Chapter
from src.backend.models.chapter_plan import ChapterPlan
from src.backend.models.topic import Topic
from src.backend.shared.connection_manager import manager
from src.llm.main import run_planner

logger = logging.getLogger(__name__)


class PlannerService:
    @staticmethod
    async def run_planner_and_finalize(topic_id: str) -> None:
        """Run the planner as a background task and update statuses when done."""
        topic_uuid = UUID(topic_id)
        try:
            logger.info("Starting planner for topic %s", topic_id)
            await PlannerService._update_topic_status(topic_uuid, TopicStatus.IN_PROGRESS)

            await run_planner(topic_id, on_progress=lambda: PlannerService._broadcast_progress(topic_id))
            
            await PlannerService._broadcast_progress(topic_id) # Final sync
            await PlannerService._unlock_first_chapter(topic_uuid)
            logger.info("Planner completed successfully for topic %s", topic_id)

        except Exception as e:
            logger.exception("Planner failed for topic %s: %s", topic_id, e)
            await PlannerService._update_topic_status(topic_uuid, TopicStatus.PENDING)

    @staticmethod
    async def _update_topic_status(topic_id: UUID, status: TopicStatus) -> None:
        """Helper to update a topic's status."""
        async with SessionLocal() as db:
            result = await db.execute(select(Topic).filter(Topic.id == topic_id))
            topic = result.scalars().first()
            if topic:
                topic.status = status
                await db.commit()

    @staticmethod
    async def _unlock_first_chapter(topic_id: UUID) -> None:
        """Unlock the first chapter of a topic to PENDING status."""
        async with SessionLocal() as db:
            result = await db.execute(
                select(Chapter)
                .filter(Chapter.topic_id == topic_id, Chapter.deleted_at.is_(None))
                .order_by(Chapter.order_index)
                .limit(1)
            )
            first_chapter = result.scalars().first()
            if first_chapter:
                first_chapter.status = ChapterStatus.PENDING
                await db.commit()

    @staticmethod
    async def _broadcast_progress(topic_id: str) -> None:
        """Fetch current status and broadcast via WebSocket."""
        async with SessionLocal() as db:
            status = await PlannerService.get_planning_status(db, UUID(topic_id))
            if "error" not in status:
                await manager.broadcast_topic_status(topic_id, status)

    @staticmethod
    async def get_planning_status(db: AsyncSession, topic_id: UUID) -> Dict[str, Any]:
        """Return planning progress for a topic."""
        result = await db.execute(select(Topic).filter(Topic.id == topic_id, Topic.deleted_at.is_(None)))
        topic = result.scalars().first()
        if not topic: 
            raise EntityNotFoundError(f"Topic not found: {topic_id}")

        total = await db.scalar(select(func.count(Chapter.id)).filter(Chapter.topic_id == topic_id, Chapter.deleted_at.is_(None)))
        planned = await db.scalar(
            select(func.count(ChapterPlan.id))
            .join(Chapter, ChapterPlan.chapter_id == Chapter.id)
            .filter(Chapter.topic_id == topic_id, Chapter.deleted_at.is_(None))
        )

        return {
            "topic_status": topic.status.value if hasattr(topic.status, 'value') else str(topic.status),
            "total_chapters": total or 0,
            "planned_chapters": planned or 0,
            "planning_complete": (total or 0) > 0 and (planned or 0) >= (total or 0),
        }

    @staticmethod
    async def recover_stalled_tasks() -> None:
        """Find and resume topics stuck in IN_PROGRESS but not fully planned."""
        try:
            async with SessionLocal() as db:
                result = await db.execute(
                    select(Topic).filter(Topic.status == TopicStatus.IN_PROGRESS, Topic.deleted_at.is_(None))
                )
                for topic in result.scalars().all():
                    status = await PlannerService.get_planning_status(db, topic.id)
                    if not status.get("planning_complete"):
                        asyncio.create_task(PlannerService.run_planner_and_finalize(str(topic.id)))
        except Exception as e:
            logger.error("Failed to recover stalled tasks: %s", e)
