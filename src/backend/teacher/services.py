import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.conversation import ConversationType
from src.backend.conversations.repository import conversation_repo
from src.backend.chapters.course_repository import course_repo
from src.backend.shared.stream_history import save_stream_results, load_chat_history
from src.llm.main import run_teacher_agent

logger = logging.getLogger(__name__)


class TeacherService:
    @staticmethod
    async def get_or_create_conversation(db: AsyncSession, user_id: UUID, chapter_id: UUID) -> Any:
        return await conversation_repo.get_or_create_by_chapter(
            db, user_id, chapter_id, ConversationType.TEACHER
        )

    @staticmethod
    async def load_chat_history(db: AsyncSession, conversation_id: UUID) -> List[Dict[str, Any]]:
        return await load_chat_history(db, conversation_id)

    @staticmethod
    async def stream_teacher(
        chapter_id: UUID, chat_history: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """Asynchronous generator that streams from the TeacherAgent."""
        async for event in run_teacher_agent(str(chapter_id), chat_history):
            yield event

    @staticmethod
    async def save_stream_results(db: AsyncSession, conversation_id: UUID, final_data: Dict[str, Any]) -> None:
        await save_stream_results(db, conversation_id, final_data)

    @classmethod
    async def update_status(cls, db: AsyncSession, chapter_id: UUID, action: str) -> str:
        """Delegate status management to the repository layer."""
        return await course_repo.update_status(db, chapter_id, action)

    @classmethod
    async def get_curriculum_context(cls, db: AsyncSession, chapter_id: UUID) -> Dict[str, Any]:
        """Delegate context fetching to the repository layer."""
        return await course_repo.get_curriculum_context(db, chapter_id)

    @staticmethod
    async def get_chapter_outline(db: AsyncSession, chapter_id: UUID) -> Dict[str, Any]:
        """Delegate outline fetching to the repository layer."""
        return await course_repo.get_chapter_outline(db, chapter_id)

