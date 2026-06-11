from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.models.user import User
from src.backend.shared.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[User]:
        result = await db.execute(select(self.model).filter(self.model.name == name))
        return result.scalars().first()


user_repo = UserRepository()
