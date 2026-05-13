import asyncio
import logging
import sys

from src.backend.db.database import Base, engine
import src.backend.models

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def init_db(confirm: bool = False) -> None:
    if not confirm:
        raise RuntimeError(
            "init_db() requires confirm=True. "
            "Run from CLI with --confirm flag to acknowledge data loss."
        )
    async with engine.begin() as conn:
        logger.info("Dropping old schema...")
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Recreating database schema...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Done!")


if __name__ == "__main__":
    if "--confirm" not in sys.argv:
        print("ERROR: Pass --confirm to acknowledge this will DROP ALL TABLES.")
        print("Usage: python -m src.backend.db.init_db --confirm")
        sys.exit(1)
    asyncio.run(init_db(confirm=True))
