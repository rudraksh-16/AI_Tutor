import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.backend.auth.routes import router as auth_router
from src.backend.common.exceptions import BaseAppError
from src.backend.db.database import engine
from src.backend.logging_config import configure_logging
from src.backend.planner.services import PlannerService
from src.backend.router import api_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()
    app = FastAPI(
        title="AI Tutor API",
        description="Backend API for the AI Tutor ChatGPT-like application",
        version="1.0.0",
        lifespan=lifespan,
    )
    _register_middleware(app)
    _register_exception_handlers(app)
    _register_routes(app)
    return app


def _validate_env() -> None:
    required = ["DATABASE_URL", "ACCESS_SECRET_KEY", "REFRESH_SECRET_KEY"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup recovery and dispose database resources on shutdown."""
    _validate_env()
    await PlannerService.recover_stalled_tasks()
    yield
    await engine.dispose()


def _register_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BaseAppError)
    async def base_app_error_handler(
        _request: Request, exc: BaseAppError
    ) -> JSONResponse:
        """Handle all domain-specific exceptions consistently."""
        logger.error("Domain error: %s | Details: %s", exc.message, exc.details)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "details": exc.details,
            },
        )


def _register_routes(app: FastAPI) -> None:
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Welcome to the AI Tutor API"}
