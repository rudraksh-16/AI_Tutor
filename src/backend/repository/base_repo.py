import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.base import BaseModel

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """Generic async repository providing CRUD operations for SQLAlchemy models."""

    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        result = await db.execute(
            select(self.model).filter(self.model.id == id, self.model.deleted_at.is_(None))
        )
        return result.scalars().first()

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ModelType]:
        result = await db.execute(
            select(self.model).filter(self.model.deleted_at.is_(None)).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, obj_in: Dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        try:
            await db.commit()
            await db.refresh(db_obj)
        except Exception:
            try:
                await db.rollback()
            except Exception as rollback_err:
                logger.warning("Rollback failed after create error: %s", rollback_err)
            raise
        return db_obj

    async def update(self, db: AsyncSession, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        try:
            await db.commit()
            await db.refresh(db_obj)
        except Exception:
            try:
                await db.rollback()
            except Exception as rollback_err:
                logger.warning("Rollback failed after update error: %s", rollback_err)
            raise
        return db_obj

    async def delete(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        obj = await self.get(db, id)
        if obj:
            setattr(obj, "deleted_at", func.now())
            try:
                await db.commit()
                await db.refresh(obj)
            except Exception:
                try:
                    await db.rollback()
                except Exception as rollback_err:
                    logger.warning("Rollback failed after delete error: %s", rollback_err)
                raise
        return obj
