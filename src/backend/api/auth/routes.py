from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.backend.db.database import get_db
from src.backend.api.auth import schemas, services
from src.backend.api.auth.schemas import TokenRefresh
from src.backend.api.auth.utils import get_current_user
from src.backend.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/register",
    response_model=schemas.UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(request: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await services.register_user(request, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error registering user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/login", response_model=schemas.Token)
async def login_user(request: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        return await services.login_user(request, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error logging in user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/me", response_model=schemas.UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns current authenticated user profile."""
    return current_user

@router.post("/refresh", response_model=schemas.Token)
async def refresh_token(request: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Refreshes the access token using a valid refresh token."""
    try:
        return await services.refresh_user_token(request.refresh_token, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error refreshing token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
