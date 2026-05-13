from typing import Optional
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
from src.backend.services.quiz_service import QuizService

router = APIRouter()


class QuizChatRequest(BaseModel):
    chapter_id: UUID
    user_message: Optional[str] = Field(None, max_length=10000)
    resume_stream: bool = False


@router.post("/quiz")
async def chat_with_quiz(
    request: QuizChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assess learner knowledge via the quiz agent."""
    await verify_chapter_ownership(db, request.chapter_id, current_user)

    conversation = await QuizService.get_or_create_conversation(
        db, current_user.id, request.chapter_id
    )
    if request.resume_stream:
        return await ChatCoordinator.create_streaming_response(
            conversation.id,
            None,
            QuizService.save_stream_results,
        )

    chat_history = await QuizService.load_chat_history(db, conversation.id)
    if await ChatCoordinator.has_active_run(conversation.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A quiz response is already streaming.",
        )
    if not request.user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_message is required.",
        )

    # 1. Persist user message
    await message_repo.add_user_message(db, conversation.id, request.user_message)
    chat_history.append({"role": "user", "content": request.user_message})

    # 2. Coordinate stream via shared logic
    agent_stream = QuizService.stream_quiz(request.chapter_id, chat_history)
    
    return await ChatCoordinator.create_streaming_response(
        conversation.id,
        agent_stream,
        QuizService.save_stream_results
    )
