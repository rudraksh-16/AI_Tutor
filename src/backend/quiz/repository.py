from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.quiz_attempt import QuizAttempt
from src.backend.models.quiz_question import QuizQuestion
from src.backend.shared.repository import BaseRepository


class QuizAttemptRepository(BaseRepository[QuizAttempt]):
    def __init__(self):
        super().__init__(QuizAttempt)

    async def get_by_chapter_and_user(
        self, db: AsyncSession, chapter_id: UUID, user_id: UUID
    ) -> List[QuizAttempt]:
        result = await db.execute(
            select(self.model)
            .filter(
                self.model.chapter_id == chapter_id,
                self.model.user_id == user_id,
                self.model.deleted_at.is_(None),
            )
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_latest(
        self, db: AsyncSession, chapter_id: UUID, user_id: UUID
    ) -> Optional[QuizAttempt]:
        result = await db.execute(
            select(self.model)
            .filter(
                self.model.chapter_id == chapter_id,
                self.model.user_id == user_id,
                self.model.deleted_at.is_(None),
            )
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()


class QuizQuestionRepository(BaseRepository[QuizQuestion]):
    def __init__(self):
        super().__init__(QuizQuestion)

    async def get_by_chapter(
        self, db: AsyncSession, chapter_id: UUID
    ) -> List[QuizQuestion]:
        result = await db.execute(
            select(self.model).filter(
                self.model.chapter_id == chapter_id,
                self.model.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())


quiz_attempt_repo = QuizAttemptRepository()
quiz_question_repo = QuizQuestionRepository()

