"""Shared service utilities to avoid code duplication across agent services."""

from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.conversations.message_repository import message_repo


async def save_stream_results(
    db: AsyncSession,
    conversation_id: UUID,
    final_data: Dict[str, Any],
) -> None:
    """Persist the agent response after a stream completes.

    Shared by CurriculumService, TeacherService, and QuizService.
    """
    tool_calls = final_data.get("tool_calls", [])
    for tc in tool_calls:
        tool_input = tc.get("input", {})
        tool_output = tc.get("output", {})

        await message_repo.add_tool_call(
            db,
            conversation_id,
            name=tool_input.get("name", ""),
            arguments=tool_input.get("arguments", "{}"),
            call_id=tool_input.get("call_id", ""),
        )
        await message_repo.add_tool_output(
            db,
            conversation_id,
            call_id=tool_output.get("call_id", ""),
            output=tool_output.get("output", ""),
        )

    assistant_text = final_data.get("assistant_text", "")
    if assistant_text.strip():
        await message_repo.add_assistant_message(db, conversation_id, assistant_text)


async def load_chat_history(db: AsyncSession, conversation_id: UUID) -> List[Dict[str, Any]]:
    """Load and convert DB messages to chat history format.

    Shared by CurriculumService, TeacherService, and QuizService.
    """
    messages = await message_repo.get_by_conversation(db, conversation_id)
    return message_repo.messages_to_chat_history(messages)
