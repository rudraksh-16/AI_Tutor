import json
from typing import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.auth.utils import get_current_user
from src.backend.api.v1.endpoints.chapters import verify_chapter_ownership
from src.backend.db.database import get_db
from src.backend.models.user import User
from src.backend.repository.message_repo import message_repo
from src.backend.services.chat_coordinator import ChatCoordinator
from src.backend.services.teacher_service import TeacherService

router = APIRouter()


class TeacherChatRequest(BaseModel):
    chapter_id: UUID
    user_message: str | None = Field(None, max_length=10000)
    resume_stream: bool = False


@router.post("/teacher")
async def chat_with_teacher(
    request: TeacherChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Engage in a teaching session for a specific chapter."""
    await verify_chapter_ownership(db, request.chapter_id, current_user)

    conversation = await TeacherService.get_or_create_conversation(
        db, current_user.id, request.chapter_id
    )
    if request.resume_stream:
        return await ChatCoordinator.create_streaming_response(
            conversation.id,
            None,
            TeacherService.save_stream_results,
            final_payload_callback=lambda data: _teacher_post_process(data, request.chapter_id)
        )

    chat_history = await TeacherService.load_chat_history(db, conversation.id)
    if await ChatCoordinator.has_active_run(conversation.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A teacher response is already streaming.",
        )
    if not request.user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_message is required.",
        )

    # 1. Persist user message
    await message_repo.add_user_message(db, conversation.id, request.user_message)
    chat_history.append({"role": "user", "content": request.user_message})

    # 2. Coordinate stream and post-processing
    agent_stream = TeacherService.stream_teacher(request.chapter_id, chat_history)
    
    return await ChatCoordinator.create_streaming_response(
        conversation.id,
        agent_stream,
        TeacherService.save_stream_results,
        final_payload_callback=lambda data: _teacher_post_process(data, request.chapter_id)
    )


async def _teacher_post_process(
    final_data: dict, chapter_id: UUID
) -> AsyncGenerator[str, None]:
    """Emit quiz notification or completion event if agent triggered a status change."""
    action = _get_status_action(final_data)
    if action == "quiz_pending":
        yield f"data: {json.dumps({'type': 'quiz_ready', 'chapter_id': str(chapter_id)})}\n\n"
    elif action == "complete":
        yield f"data: {json.dumps({'type': 'chapter_completed', 'chapter_id': str(chapter_id)})}\n\n"


def _get_status_action(final_data: dict) -> str | None:
    """Check tool calls to determine if the chapter transitioned to a new state."""
    for tc in final_data.get("tool_calls", []):
        tool_input = tc.get("input", {})
        if tool_input.get("name") != "update_status_tool":
            continue
        try:
            args = json.loads(tool_input.get("arguments", "{}"))
            action = args.get("action")
            if action in ("complete", "quiz_pending"):
                return action
        except (json.JSONDecodeError, TypeError):
            continue
    return None
