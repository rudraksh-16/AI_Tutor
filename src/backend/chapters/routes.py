from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.utils import get_current_user
from src.backend.db.database import get_db
from src.backend.enums.status import ChapterStatus
from src.backend.chapters.repository import chapter_repo
from src.backend.conversations.message_repository import message_repo
from src.backend.quiz.repository import quiz_attempt_repo
from src.backend.quiz.schemas import QuizStatePayload, QuizStateResponse
from src.backend.chapters.schemas import ChapterRead
from src.backend.teacher.services import TeacherService
from src.backend.models.user import User
from src.backend.shared.authorization import verify_chapter_ownership

router = APIRouter()
PASS_THRESHOLD = 0.7


@router.get("/{chapter_id}", response_model=ChapterRead)
async def get_chapter(
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChapterRead:
    chapter_obj = await verify_chapter_ownership(db, chapter_id, current_user)
    return chapter_obj


@router.post("/{chapter_id}/complete", response_model=ChapterRead)
async def complete_chapter(
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChapterRead:
    """Mark a chapter as completed (after quiz pass) and unlock the next one."""
    chapter_obj = await verify_chapter_ownership(db, chapter_id, current_user)

    updated_chapter = await chapter_repo.update(
        db, chapter_obj, {"status": ChapterStatus.COMPLETED.value}
    )

    # Unlock next chapter to PENDING (accessible but not started)
    next_chapter = await chapter_repo.get_next_chapter(
        db, chapter_obj.topic_id, chapter_obj.order_index
    )
    if next_chapter:
        await chapter_repo.update(db, next_chapter, {"status": ChapterStatus.PENDING.value})

    return updated_chapter


@router.get("/{chapter_id}/quiz-state", response_model=Optional[QuizStateResponse])
async def get_quiz_state(
    chapter_id: UUID,
    quiz_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Optional[QuizStateResponse]:
    """Return the latest persisted quiz state for the teacher-generated quiz."""
    chapter_obj = await verify_chapter_ownership(db, chapter_id, current_user)
    conversation = await TeacherService.get_or_create_conversation(db, current_user.id, chapter_id)
    state_message = await message_repo.get_latest_quiz_state(db, conversation.id, quiz_key)

    if not state_message or not state_message.meta:
        return None

    meta = state_message.meta
    return QuizStateResponse(
        quiz_key=meta.get("quiz_key", quiz_key),
        selected_answers=meta.get("selected_answers", {}),
        submitted=meta.get("submitted", False),
        score=meta.get("score"),
        total=meta.get("total"),
        passed=meta.get("passed"),
        feedback=meta.get("feedback", []),
        chapter_status=chapter_obj.status.value if hasattr(chapter_obj.status, "value") else str(chapter_obj.status),
        saved_at=state_message.updated_at.isoformat() if state_message.updated_at else None,
    )


@router.put("/{chapter_id}/quiz-state", response_model=QuizStateResponse)
async def save_quiz_state(
    chapter_id: UUID,
    payload: QuizStatePayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuizStateResponse:
    """Persist quiz draft answers and submitted quiz results for the teacher flow."""
    chapter_obj = await verify_chapter_ownership(db, chapter_id, current_user)
    conversation = await TeacherService.get_or_create_conversation(db, current_user.id, chapter_id)

    state_payload: Dict[str, Any] = {
        "selected_answers": payload.selected_answers,
        "submitted": payload.submitted,
        "score": payload.score,
        "total": payload.total,
        "passed": payload.passed,
        "feedback": [item.model_dump() for item in payload.feedback],
    }

    computed_passed = payload.passed
    if payload.submitted:
        total = payload.total or 0
        score = payload.score or 0
        computed_passed = (score / total) >= PASS_THRESHOLD if total > 0 else False
        state_payload["passed"] = computed_passed

    state_message = await message_repo.save_quiz_state(
        db,
        conversation.id,
        payload.quiz_key,
        state_payload,
    )

    if payload.submitted:
        await quiz_attempt_repo.create(
            db,
            {
                "chapter_id": chapter_id,
                "user_id": current_user.id,
                "score": payload.score or 0,
                "total_questions": payload.total or 0,
                "passed": bool(computed_passed),
            },
        )

        if computed_passed and chapter_obj.status != ChapterStatus.COMPLETED:
            await TeacherService.update_status(db, chapter_id, "complete")
            chapter_obj = await chapter_repo.get(db, chapter_id)

    return QuizStateResponse(
        quiz_key=payload.quiz_key,
        selected_answers=payload.selected_answers,
        submitted=payload.submitted,
        score=payload.score,
        total=payload.total,
        passed=computed_passed,
        feedback=payload.feedback,
        chapter_status=chapter_obj.status.value if hasattr(chapter_obj.status, "value") else str(chapter_obj.status),
        saved_at=state_message.updated_at.isoformat() if state_message.updated_at else None,
    )
