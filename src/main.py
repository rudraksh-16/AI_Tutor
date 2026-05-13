import logging.config
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.backend.api.v1.router import api_router
from src.backend.api.auth.routes import router as auth_router
from src.backend.config import Config
from src.llm.config import LLMConfig
from src.backend.db.database import engine
from src.backend.services.planner_service import PlannerService
from src.backend.common.exceptions import BaseAppError


def _validate_env() -> None:
    required = ["DATABASE_URL", "ACCESS_SECRET_KEY", "REFRESH_SECRET_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Standardize log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = LLMConfig.LOG_LEVEL

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": LOG_FORMAT},
    },
    "handlers": {
        "console": {
            "level": "INFO",  # Keep terminal clean: no DEBUG logs here
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "app_file": {
            "level": "DEBUG", # Full history in the main log file
            "class": "logging.FileHandler",
            "filename": "logs/app.log",
            "formatter": "standard",
        },
        "planner_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "logs/planner.log",
            "formatter": "standard",
        },
        "curriculum_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "logs/curriculum.log",
            "formatter": "standard",
        },
        "teacher_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "logs/teacher.log",
            "formatter": "standard",
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["console", "app_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "src.llm.planner": {
            "handlers": ["planner_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "src.backend.services.planner_service": {
            "handlers": ["planner_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "src.llm.curriculum_agent": {
            "handlers": ["curriculum_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "src.backend.api.v1.endpoints.chat_curriculum": {
            "handlers": ["curriculum_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "src.llm.teacher_agent": {
            "handlers": ["teacher_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "src.llm.quiz_agent": {
            "handlers": ["teacher_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "src.backend.api.v1.endpoints.chat_teacher": {
            "handlers": ["teacher_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "src.backend.api.v1.endpoints.chat_quiz": {
            "handlers": ["teacher_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "src.backend.services.teacher_service": {
            "handlers": ["teacher_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "src.backend.services.quiz_service": {
            "handlers": ["teacher_file"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_env()
    await PlannerService.recover_stalled_tasks()
    yield
    await engine.dispose()

app = FastAPI(
    title="AI Tutor API",
    description="Backend API for the AI Tutor ChatGPT-like application",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

@app.exception_handler(BaseAppError)
async def base_app_error_handler(request: Request, exc: BaseAppError):
    """Global handler for all domain-specific exceptions."""
    logger.error("Domain error: %s | Details: %s", exc.message, exc.details)
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.message, "details": exc.details},
    )


# Auth routes at /api/auth/ (per architecture doc)
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

# V1 API routes at /api/v1/
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Welcome to the AI Tutor API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
