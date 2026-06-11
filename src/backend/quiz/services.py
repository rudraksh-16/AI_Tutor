from typing import List, Dict, Any, AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.conversation import ConversationType
from src.backend.conversations.repository import conversation_repo
from src.backend.shared.stream_history import save_stream_results, load_chat_history
from src.llm.quiz_agent.agent import QuizAgent
from src.llm.quiz_agent.constant import QuizConstants


class QuizService:
    @staticmethod
    async def get_or_create_conversation(db: AsyncSession, user_id: UUID, chapter_id: UUID) -> Any:
        return await conversation_repo.get_or_create_by_chapter(
            db, user_id, chapter_id, ConversationType.QUIZ
        )

    @staticmethod
    async def load_chat_history(db: AsyncSession, conversation_id: UUID) -> List[Dict[str, Any]]:
        return await load_chat_history(db, conversation_id)

    @staticmethod
    async def stream_quiz(
        chapter_id: UUID, chat_history: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """Asynchronous generator that streams from the QuizAgent."""
        agent = QuizAgent(
            chapter_id=str(chapter_id),
            model=QuizConstants.MODEL,
            max_iteration=QuizConstants.MAX_ITERATION,
            temperature=QuizConstants.TEMPERATURE,
        )
        async for event in agent.astream(chat_history):
            yield event

    @staticmethod
    async def save_stream_results(db: AsyncSession, conversation_id: UUID, final_data: Dict[str, Any]) -> None:
        await save_stream_results(db, conversation_id, final_data)
