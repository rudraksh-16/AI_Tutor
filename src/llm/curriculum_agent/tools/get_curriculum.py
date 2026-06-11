import logging
from typing import Dict, Any
from uuid import UUID

from src.backend.db.database import SessionLocal
from src.backend.curriculum.repository import curriculum_repo
from src.llm.agent_core.tool import Tool

logger = logging.getLogger(__name__)

def make_get_curriculum_tool(topic_id: str) -> Tool:
    """Factory to create a tool mapping the topic structure."""
    
    async def get_curriculum_tool() -> Dict[str, Any]:
        """Call CurriculumRepository to fetch the topic content."""
        async with SessionLocal() as db:
            data = await curriculum_repo.get_curriculum_data(db, UUID(topic_id))
            return {"status": "success", **data}

    return Tool(
        func=get_curriculum_tool,
        description="Fetch the saved curriculum for the active topic.",
    )
