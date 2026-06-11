import logging
from uuid import UUID

from src.backend.db.database import SessionLocal
from src.backend.chapters.course_repository import course_repo
from src.llm.agent_core.args_schema import ArgsSchema as Args
from src.llm.agent_core.tool import Tool

logger = logging.getLogger(__name__)

class UpdateChapterStatus:
    args = [
        (
            "action",
            Args(
                type=str,
                description="Status action for the chapter",
                required=True,
                enum=["start", "complete", "quiz_pending"],
            ),
        ),
    ]

def make_update_status(chapter_id: str) -> Tool:
    """Factory to create a chapter status update tool."""
    
    async def update_status_tool(action: str) -> str:
        """Call CourseRepository to update the chapter and topic state."""
        async with SessionLocal() as db:
            result = await course_repo.update_status(db, UUID(chapter_id), action)
            logger.info("Status updated: %s", result)
            return result

    return Tool(
        func=update_status_tool,
        description="Update the status of the current chapter (start, complete, quiz_pending)",
        args_schema=UpdateChapterStatus,
    )
