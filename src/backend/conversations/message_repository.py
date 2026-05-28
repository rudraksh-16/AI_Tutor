from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.message import Message, MessageRole
from src.backend.shared.repository import BaseRepository


class MessageRepository(BaseRepository[Message]):
    def __init__(self):
        super().__init__(Message)

    async def get_by_conversation(
        self, db: AsyncSession, conversation_id: UUID
    ) -> List[Message]:
        """Fetch all messages for a conversation, ordered by sequence."""
        result = await db.execute(
            select(self.model)
            .filter(
                self.model.conversation_id == conversation_id,
                self.model.deleted_at.is_(None),
            )
            .order_by(self.model.sequence)
        )
        return list(result.scalars().all())

    async def get_next_sequence(self, db: AsyncSession, conversation_id: UUID) -> int:
        """Get the next available sequence number for a conversation."""
        result = await db.execute(
            select(func.coalesce(func.max(self.model.sequence), 0))
            .filter(self.model.conversation_id == conversation_id)
        )
        return result.scalar() + 1

    async def add_user_message(
        self, db: AsyncSession, conversation_id: UUID, content: str
    ) -> Message:
        """Save a user message to the conversation."""
        seq = await self.get_next_sequence(db, conversation_id)
        msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content,
            sequence=seq,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    async def add_assistant_message(
        self, db: AsyncSession, conversation_id: UUID, content: str
    ) -> Message:
        """Save an assistant text response to the conversation."""
        seq = await self.get_next_sequence(db, conversation_id)
        msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            sequence=seq,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    async def add_system_message(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        content: str = "",
        meta: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Save a system message to the conversation."""
        seq = await self.get_next_sequence(db, conversation_id)
        msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.SYSTEM,
            content=content,
            sequence=seq,
            meta=meta,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    async def add_tool_call(
        self, db: AsyncSession, conversation_id: UUID, name: str, arguments: str, call_id: str
    ) -> Message:
        """Save a tool call event to the conversation."""
        seq = await self.get_next_sequence(db, conversation_id)
        msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.TOOL_CALL,
            content=None,
            sequence=seq,
            meta={"type": "function_call", "name": name, "arguments": arguments, "call_id": call_id},
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    async def add_tool_output(
        self, db: AsyncSession, conversation_id: UUID, call_id: str, output: str
    ) -> Message:
        """Save a tool output event to the conversation."""
        seq = await self.get_next_sequence(db, conversation_id)
        msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.TOOL_OUTPUT,
            content=None,
            sequence=seq,
            meta={"type": "function_call_output", "call_id": call_id, "output": output},
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    async def get_latest_quiz_state(
        self, db: AsyncSession, conversation_id: UUID, quiz_key: str
    ) -> Optional[Message]:
        """Return the most recent persisted quiz state for a quiz key."""
        messages = await self.get_by_conversation(db, conversation_id)
        for msg in reversed(messages):
            if msg.role != MessageRole.SYSTEM or not msg.meta:
                continue
            if msg.meta.get("type") != "quiz_state":
                continue
            if msg.meta.get("quiz_key") != quiz_key:
                continue
            return msg
        return None

    async def save_quiz_state(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        quiz_key: str,
        payload: Dict[str, Any],
    ) -> Message:
        """Persist resumable quiz state in the teacher conversation."""
        existing = await self.get_latest_quiz_state(db, conversation_id, quiz_key)
        meta = {"type": "quiz_state", "quiz_key": quiz_key, **payload}

        if existing:
            existing.meta = meta
            await db.commit()
            await db.refresh(existing)
            return existing

        return await self.add_system_message(
            db,
            conversation_id,
            content="quiz_state",
            meta=meta,
        )

    def messages_to_chat_history(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert DB messages into the OpenAI-compatible chat_history list the agents expect."""
        history = []
        for msg in messages:
            if msg.role == MessageRole.USER:
                history.append({"role": "user", "content": msg.content})
            elif msg.role == MessageRole.ASSISTANT:
                history.append({"role": "assistant", "content": msg.content})
            elif msg.role == MessageRole.SYSTEM:
                if msg.meta and msg.meta.get("type") == "quiz_state":
                    continue
                history.append({"role": "system", "content": msg.content})
            elif msg.role == MessageRole.TOOL_CALL:
                history.append(msg.meta)
            elif msg.role == MessageRole.TOOL_OUTPUT:
                history.append(msg.meta)
        return history


message_repo = MessageRepository()
