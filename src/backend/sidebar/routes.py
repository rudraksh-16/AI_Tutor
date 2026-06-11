from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import and_, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.utils import get_current_user
from src.backend.db.database import get_db
from src.backend.enums.status import TopicStatus
from src.backend.models.chapter import Chapter
from src.backend.models.chapter_plan import ChapterPlan
from src.backend.models.topic import Topic
from src.backend.models.user import User
from src.backend.sidebar.schemas import SidebarResponse, SidebarTopicItem

router = APIRouter()


async def _get_sidebar_topic_items(
    db: AsyncSession,
    user_id: UUID,
) -> list[SidebarTopicItem]:
    """Return sidebar topics with planning completion in one query."""
    result = await db.execute(
        select(
            Topic.id,
            Topic.title,
            Topic.status,
            func.count(distinct(Chapter.id)).label("total_chapters"),
            func.count(ChapterPlan.id).label("planned_chapters"),
        )
        .outerjoin(
            Chapter,
            and_(
                Chapter.topic_id == Topic.id,
                Chapter.deleted_at.is_(None),
            ),
        )
        .outerjoin(
            ChapterPlan,
            and_(
                ChapterPlan.chapter_id == Chapter.id,
                ChapterPlan.deleted_at.is_(None),
            ),
        )
        .filter(Topic.user_id == user_id, Topic.deleted_at.is_(None))
        .group_by(Topic.id, Topic.title, Topic.status, Topic.created_at)
        .order_by(Topic.created_at.desc())
    )

    return [
        SidebarTopicItem(
            id=topic_id,
            title=title,
            status=topic_status,
            planning_complete=total_chapters > 0 and planned_chapters >= total_chapters,
        )
        for topic_id, title, topic_status, total_chapters, planned_chapters in result.all()
    ]


@router.get("/", response_model=SidebarResponse)
async def get_sidebar(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SidebarResponse:
    """Return topics grouped into in_progress and completed."""
    topics = await _get_sidebar_topic_items(db, current_user.id)

    in_progress = []
    completed = []

    for topic in topics:
        if topic.status == TopicStatus.COMPLETED:
            completed.append(topic)
        else:
            # PENDING and IN_PROGRESS both go to the incomplete bucket
            in_progress.append(topic)

    return SidebarResponse(in_progress=in_progress, completed=completed)
