from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.conversation import Conversation, ConversationType
from src.backend.shared.repository import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self):
        super().__init__(Conversation)

    async def get_or_create_by_topic(
        self, db: AsyncSession, user_id: UUID, topic_id: UUID
    ) -> Conversation:
        """Get existing curriculum conversation for a topic, or create one."""
        result = await db.execute(
            select(self.model).filter(
                self.model.topic_id == topic_id,
                self.model.user_id == user_id,
                self.model.type == ConversationType.CURRICULUM,
                self.model.deleted_at.is_(None),
            )
        )
        conv = result.scalars().first()
        if conv:
            return conv

        conv = Conversation(
            user_id=user_id,
            topic_id=topic_id,
            type=ConversationType.CURRICULUM,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return conv

    async def get_or_create_by_chapter(
        self, db: AsyncSession, user_id: UUID, chapter_id: UUID, conv_type: ConversationType
    ) -> Conversation:
        """Get existing teacher/quiz conversation for a chapter, or create one."""
        result = await db.execute(
            select(self.model).filter(
                self.model.chapter_id == chapter_id,
                self.model.user_id == user_id,
                self.model.type == conv_type,
                self.model.deleted_at.is_(None),
            )
        )
        conv = result.scalars().first()
        if conv:
            return conv

        conv = Conversation(
            user_id=user_id,
            chapter_id=chapter_id,
            type=conv_type,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return conv

    async def get_with_messages(self, db: AsyncSession, conversation_id: UUID) -> Optional[Conversation]:
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.messages))
            .filter(self.model.id == conversation_id, self.model.deleted_at.is_(None))
        )
        return result.scalars().first()

    async def get_by_user(self, db: AsyncSession, user_id: UUID) -> List[Conversation]:
        result = await db.execute(
            select(self.model)
            .filter(self.model.user_id == user_id, self.model.deleted_at.is_(None))
            .order_by(self.model.updated_at.desc())
        )
        return list(result.scalars().all())


conversation_repo = ConversationRepository()
