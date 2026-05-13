import asyncio
import json
import logging
from typing import Optional, List, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.auth.utils import get_current_user
from src.backend.db.database import get_db
from src.backend.models.user import User
from src.backend.repository.message_repo import message_repo
from src.backend.repository.topic_repo import topic_repo
from src.backend.services.chat_coordinator import ChatCoordinator
from src.backend.services.curriculum_service import CurriculumService
from src.backend.services.planner_service import PlannerService

logger = logging.getLogger(__name__)

router = APIRouter()


class CurriculumChatRequest(BaseModel):
    topic_id: UUID
    user_message: Optional[str] = Field(None, max_length=10000)
    resume_stream: bool = False


class ChapterAccept(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    items: List[str]


class CurriculumPlanRequest(BaseModel):
    topicTitle: Optional[str] = Field(None, max_length=256)
    chapters: List[ChapterAccept] = []


@router.post("/curriculum")
async def chat_with_curriculum(
    request: CurriculumChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Chat with the curriculum agent to negotiate the learning path."""
    conversation = await CurriculumService.get_or_create_conversation(
        db, current_user.id, request.topic_id
    )
    if request.resume_stream:
        return await ChatCoordinator.create_streaming_response(
            conversation.id,
            None,
            CurriculumService.save_stream_results,
            final_payload_callback=lambda data: _curriculum_post_process(data, request.topic_id)
        )

    chat_history = await CurriculumService.load_chat_history(db, conversation.id)
    if await ChatCoordinator.has_active_run(conversation.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A curriculum response is already streaming for this topic.",
        )

    # 1. Process Initial/Auto-start Message
    user_msg = await _get_effective_user_message(db, request, chat_history)
    if not user_msg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user message is required once the curriculum chat has started.",
        )
    if user_msg:
        await message_repo.add_user_message(db, conversation.id, user_msg)
        chat_history.append({"role": "user", "content": user_msg})

    # 2. Delegate streaming to Coordinator
    agent_stream = CurriculumService.stream_curriculum(
        current_user.id, request.topic_id, chat_history
    )
    
    return await ChatCoordinator.create_streaming_response(
        conversation.id,
        agent_stream,
        CurriculumService.save_stream_results,
        final_payload_callback=lambda data: _curriculum_post_process(data, request.topic_id)
    )


async def _get_effective_user_message(
    db: AsyncSession, request: CurriculumChatRequest, history: List[dict]
) -> Optional[str]:
    """Determine the user message, falling back to topic summary for auto-start."""
    if request.user_message:
        return request.user_message.strip()
    
    if not history:
        topic = await topic_repo.get(db, request.topic_id)
        return topic.user_summary if topic else None
    return None


async def _curriculum_post_process(collected_final: dict, topic_id: UUID) -> AsyncGenerator[str, None]:
    """Trigger background planning if curriculum was updated."""
    tool_calls = collected_final.get("tool_calls", [])
    has_upsert = any(tc.get("input", {}).get("name") == "upsert_curriculum_tool" for tc in tool_calls)
    
    if has_upsert:
        logger.info("Curriculum saved for topic %s, auto-triggering planner", topic_id)
        yield f"data: {json.dumps({'type': 'planning_started'})}\n\n"
        asyncio.create_task(PlannerService.run_planner_and_finalize(str(topic_id)))


@router.post("/curriculum/{topic_id}/plan")
async def trigger_planner(
    topic_id: UUID,
    request: CurriculumPlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Save curriculum from frontend directly and trigger the planner."""
    await CurriculumService.overwrite_topic_curriculum(
        db, topic_id, request.topicTitle, request.chapters
    )
    
    asyncio.create_task(PlannerService.run_planner_and_finalize(str(topic_id)))
    return {"status": "success", "message": "Planner triggered in background"}
