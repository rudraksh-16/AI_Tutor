import logging
from typing import Dict, Any
from uuid import UUID

from src.backend.db.database import SessionLocal
from src.backend.chapters.course_repository import course_repo
from src.llm.agent_core.tool import Tool

logger = logging.getLogger(__name__)


def make_get_outline_content(chapter_id: str):
    async def get_chapter_content_tool() -> Dict[str, Any]:
        """Load the full chapter teaching plan content via CourseRepository."""
        async with SessionLocal() as db:
            return await course_repo.get_chapter_full_plan(db, UUID(chapter_id))

    return Tool(
        func=get_chapter_content_tool,
        description="Load the full chapter teaching plan content for the current chapter.",
    )


async def get_outline_content(chapter_id: str) -> str:
    """Load the full chapter plan content (standalone helper)."""
    async with SessionLocal() as db:
        try:
            chapter_uuid = UUID(chapter_id)
            query = (
                select(ChapterPlan.content)
                .filter(ChapterPlan.chapter_id == chapter_uuid)
                .limit(1)
            )
            res = await db.execute(query)
            return res.scalar()

        except Exception as e:
            logger.exception("Failed to load chapter plan for chapter_id=%s", chapter_id)
            raise RuntimeError(f"Failed to load chapter plan: {e}") from e
