import logging
from typing import Dict, Any
from uuid import UUID

from src.backend.db.database import SessionLocal
from src.backend.curriculum.repository import curriculum_repo
from src.llm.agent_core.args_schema import ArgsSchema as Args
from src.llm.agent_core.tool import Tool

logger = logging.getLogger(__name__)

class UpsertCurriculumArgs:
    args = [
        ("topic", Args(type=str, description="The title of topic")),
        ("chapter_number", Args(type=int, description="Chapter order_index number")),
        ("chapter_title", Args(type=str, description="Chapter title")),
        ("chapter_outline", Args(type=str, description="Detailed chapter description/outline")),
        ("user_summary", Args(type=str, description="Summary of user's learning intent")),
    ]

def make_upsert_curriculum_tool(user_id: str, topic_id: str) -> Tool:
    """Factory to create a tool for persisting curriculum chapters."""
    
    async def upsert_curriculum_tool(topic: str, chapter_number: int, chapter_title: str, 
                                     chapter_outline: str, user_summary: str) -> Dict[str, str]:
        """Call CurriculumRepository to persist the chapter data."""
        async with SessionLocal() as db:
            await curriculum_repo.upsert_curriculum_item(
                db, UUID(user_id), UUID(topic_id), topic, 
                chapter_number, chapter_title, chapter_outline, user_summary
            )
            return {"status": "success", "message": "Curriculum saved successfully"}

    return Tool(
        func=upsert_curriculum_tool,
        description="Save or update a curriculum chapter based on the provided input.",
        args_schema=UpsertCurriculumArgs,
    )
