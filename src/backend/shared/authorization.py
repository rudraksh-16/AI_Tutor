from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.common.exceptions import EntityNotFoundError
from src.backend.chapters.repository import chapter_repo
from src.backend.chapters.schemas import ChapterRead
from src.backend.topics.repository import topic_repo
from src.backend.models.user import User


async def verify_chapter_ownership(
    db: AsyncSession, chapter_id: UUID, current_user: User
) -> ChapterRead:
    """Return a chapter only when it belongs to the current user."""
    chapter_obj = await chapter_repo.get(db, chapter_id)
    if not chapter_obj:
        raise EntityNotFoundError(f"Chapter not found: {chapter_id}")

    topic_obj = await topic_repo.get(db, chapter_obj.topic_id)
    if not topic_obj or str(topic_obj.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return chapter_obj

