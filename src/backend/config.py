import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL")

    # Fallback if ASYNC_DATABASE_URL isn't explicitly set, convert the sync URL
    if not ASYNC_DATABASE_URL and DATABASE_URL:
        ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    # Auth
    ACCESS_SECRET_KEY: str = os.environ["ACCESS_SECRET_KEY"]
    REFRESH_SECRET_KEY: str = os.environ["REFRESH_SECRET_KEY"]
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    