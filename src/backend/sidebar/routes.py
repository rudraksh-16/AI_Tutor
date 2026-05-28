from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.db.database import get_db
from src.backend.topics.repository import topic_repo
from src.backend.sidebar.schemas import SidebarResponse, SidebarTopicItem
from src.backend.enums.status import TopicStatus
from src.backend.auth.utils import get_current_user
from src.backend.models.user import User

router = APIRouter()


@router.get("/", response_model=SidebarResponse)
async def get_sidebar(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return topics grouped into in_progress and completed."""
    topics = await topic_repo.get_by_user(db, current_user.id)

    in_progress = []
    completed = []

    for t in topics:
        item = SidebarTopicItem.model_validate(t)
        if t.status == TopicStatus.COMPLETED:
            completed.append(item)
        else:
            # PENDING and IN_PROGRESS both go to the incomplete bucket
            in_progress.append(item)

    return SidebarResponse(in_progress=in_progress, completed=completed)
