from typing import Dict, Any
from uuid import UUID

from src.backend.db.database import SessionLocal
from src.backend.chapters.course_repository import course_repo
from src.llm.agent_core.tool import Tool


def make_get_outline_content(chapter_id: str):
    async def get_chapter_content_tool() -> Dict[str, Any]:
        """Load the full chapter plan content for quiz generation via CourseRepository."""
        async with SessionLocal() as db:
            return await course_repo.get_chapter_full_plan(db, UUID(chapter_id))

    return Tool(
        func=get_chapter_content_tool,
        description="Load the full chapter plan content for quiz question generation.",
    )
