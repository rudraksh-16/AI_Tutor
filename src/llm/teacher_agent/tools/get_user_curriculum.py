import logging
from typing import Dict, Any
from uuid import UUID

from src.backend.db.database import SessionLocal
from src.backend.chapters.course_repository import course_repo
from src.llm.agent_core.tool import Tool

logger = logging.getLogger(__name__)

def make_get_user_curriculum(chapter_id: str) -> Tool:
    """Factory to create a tool that fetches the full course curriculum."""
    
    async def get_user_curriculum_tool() -> Dict[str, Any]:
        """Fetch curriculum context (topic and chapters) via CourseRepository."""
        async with SessionLocal() as db:
            result = await course_repo.get_curriculum_context(db, UUID(chapter_id))
            logger.debug("Curriculum loaded for chapter %s", chapter_id)
            return result

    return Tool(
        func=get_user_curriculum_tool,
        description="Fetch the full topic curriculum and chapter list for reference.",
    )
