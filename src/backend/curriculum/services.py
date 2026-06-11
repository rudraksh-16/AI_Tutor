import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.common.exceptions import EntityNotFoundError
from src.backend.enums.status import ChapterStatus
from src.backend.topics.repository import topic_repo
from src.backend.models.chapter import Chapter
from src.backend.conversations.repository import conversation_repo
from src.backend.curriculum.repository import curriculum_repo
from src.backend.shared.stream_history import save_stream_results, load_chat_history
from src.llm.main import run_curriculum_agent

logger = logging.getLogger(__name__)


class CurriculumService:
    @staticmethod
    async def get_or_create_conversation(db: AsyncSession, user_id: UUID, topic_id: UUID) -> Any:
        return await conversation_repo.get_or_create_by_topic(db, user_id, topic_id)

    @staticmethod
    async def load_chat_history(db: AsyncSession, conversation_id: UUID) -> List[Dict[str, Any]]:
        return await load_chat_history(db, conversation_id)

    @staticmethod
    async def stream_curriculum(
        user_id: UUID, topic_id: UUID, chat_history: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """Asynchronous generator that streams from the LLM agent."""
        async for event in run_curriculum_agent(str(user_id), str(topic_id), chat_history):
            yield event

    @staticmethod
    async def save_stream_results(db: AsyncSession, conversation_id: UUID, final_data: Dict[str, Any]) -> None:
        await save_stream_results(db, conversation_id, final_data)

    @classmethod
    async def upsert_curriculum_item(
        cls, 
        db: AsyncSession, 
        user_id: UUID, 
        topic_id: UUID, 
        topic_title: str,
        chapter_number: int,
        chapter_title: str,
        chapter_outline: str,
        user_summary: str
    ) -> None:
        """Delegate curriculum saving to the repository layer."""
        await curriculum_repo.upsert_curriculum_item(
            db, user_id, topic_id, topic_title, 
            chapter_number, chapter_title, chapter_outline, user_summary
        )

    @staticmethod
    async def get_curriculum_data(db: AsyncSession, topic_id: UUID) -> Dict[str, Any]:
        """Delegate data fetching to the repository layer."""
        return await curriculum_repo.get_curriculum_data(db, topic_id)

    @classmethod
    async def overwrite_topic_curriculum(
        cls, 
        db: AsyncSession, 
        topic_id: UUID, 
        new_title: Optional[str], 
        chapters_data: List[Any]
    ) -> None:
        """This method will be refactored further if needed; currently delegates to model."""
        topic = await topic_repo.get(db, topic_id)
        if not topic:
            raise EntityNotFoundError(f"Topic not found: {topic_id}")
        
        if new_title:
            topic.title = new_title

        await db.execute(delete(Chapter).where(Chapter.topic_id == topic_id))
        
        for idx, chap in enumerate(chapters_data):
            description = "\n".join(f"- {item}" for item in getattr(chap, 'items', []))
            db.add(Chapter(
                topic_id=topic_id,
                title=chap.title,
                order_index=idx + 1,
                description=description,
                status=ChapterStatus.LOCKED.value
            ))
        await db.commit()
