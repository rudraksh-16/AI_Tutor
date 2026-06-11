import logging
from typing import Dict, Any
from uuid import UUID

from src.backend.db.database import SessionLocal
from src.backend.chapters.course_repository import course_repo
from src.llm.agent_core.tool import Tool

logger = logging.getLogger(__name__)

def make_get_chapter(chapter_id: str) -> Tool:
    """Factory to create a tool that fetches the specific chapter outline."""
    
    async def get_chapter_tool() -> Dict[str, Any]:
        """Fetch chapter outline (ChapterPlan items) via CourseRepository."""
        async with SessionLocal() as db:
            return await course_repo.get_chapter_outline(db, UUID(chapter_id))

    return Tool(
        func=get_chapter_tool,
        description="Fetch the detailed outline (points) for the active chapter.",
    )
