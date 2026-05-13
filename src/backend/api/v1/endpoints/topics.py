import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.auth.utils import get_current_user, get_ws_user
from src.backend.api.ws.connection_manager import manager
from src.backend.common.exceptions import EntityNotFoundError
from src.backend.db.database import get_db
from src.backend.models.topic import Topic
from src.backend.models.user import User
from src.backend.repository.chapter_repo import chapter_repo
from src.backend.repository.topic_repo import topic_repo
from src.backend.schemas.chapter import ChapterRead
from src.backend.schemas.topic import TopicCreate, TopicRead
from src.backend.services.planner_service import PlannerService

logger = logging.getLogger(__name__)

router = APIRouter()


class TopicStartRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    user_summary: str = Field(..., min_length=1, max_length=5000)


class PlanningStatusResponse(BaseModel):
    topic_status: str
    total_chapters: int
    planned_chapters: int
    planning_complete: bool


@router.post("/", response_model=TopicRead)
async def create_topic(
    topic_in: TopicCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicRead:
    if str(current_user.id) != str(topic_in.user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    topic_obj = await topic_repo.create(
        db, {"title": topic_in.title, "user_summary": topic_in.user_summary, "user_id": topic_in.user_id}
    )
    return topic_obj


@router.post("/start", response_model=TopicRead)
async def start_topic(
    request: TopicStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicRead:
    """Simplified topic creation: just title + summary, user_id from auth token."""
    topic_obj = await topic_repo.create(
        db, {
            "title": request.title,
            "user_summary": request.user_summary,
            "user_id": current_user.id,
        }
    )
    return topic_obj


@router.get("/{topic_id}", response_model=TopicRead)
async def get_topic(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicRead:
    """Fetch a single topic by ID."""
    topic_obj = await topic_repo.get_with_chapters(db, topic_id)
    if not topic_obj:
        raise EntityNotFoundError(f"Topic not found: {topic_id}")
    
    if str(topic_obj.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return topic_obj


@router.get("/{topic_id}/chapters", response_model=List[ChapterRead])
async def get_topic_chapters(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ChapterRead]:
    """Fetch all chapters for a specific topic."""
    topic_obj = await topic_repo.get(db, topic_id)
    if not topic_obj:
        raise EntityNotFoundError(f"Topic not found: {topic_id}")
    
    if str(topic_obj.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    chapters = await chapter_repo.get_by_topic(db, topic_id)
    return chapters


@router.get("/{topic_id}/status", response_model=PlanningStatusResponse)
async def get_planning_status(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlanningStatusResponse:
    """Get the planning progress for a topic (used by frontend to poll)."""
    topic_obj = await topic_repo.get(db, topic_id)
    if not topic_obj:
        raise EntityNotFoundError(f"Topic not found: {topic_id}")
    
    if str(topic_obj.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    result = await PlannerService.get_planning_status(db, topic_id)
    return result


async def _authorize_ws_topic(
    websocket: WebSocket,
    topic_id: UUID,
    token: Optional[str],
    db: AsyncSession,
) -> bool:
    """Verify token and topic ownership. Closes socket with 1008 and returns False on failure."""
    try:
        current_user = await get_ws_user(token or "", db)
    except HTTPException:
        await websocket.close(code=1008)
        return False

    topic_obj = await topic_repo.get(db, topic_id)
    if not topic_obj or str(topic_obj.user_id) != str(current_user.id):
        await websocket.close(code=1008)
        return False

    return True


@router.websocket("/{topic_id}/status/ws")
async def websocket_planning_status(
    websocket: WebSocket,
    topic_id: UUID,
    token: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Push live planning status over WebSocket. Auth via ?token= query param."""
    await websocket.accept()

    if not await _authorize_ws_topic(websocket, topic_id, token, db):
        return

    topic_key = str(topic_id)
    if topic_key not in manager.active_connections:
        manager.active_connections[topic_key] = []
    manager.active_connections[topic_key].append(websocket)

    try:
        initial_status = await PlannerService.get_planning_status(db, topic_id)
        if "error" not in initial_status:
            await websocket.send_json(initial_status)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, topic_key)
    except Exception:
        logger.error("Unexpected error in WebSocket handler for topic %s", topic_id, exc_info=True)
        manager.disconnect(websocket, topic_key)

