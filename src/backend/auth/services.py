from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.schemas import Token, UserCreate, UserLogin, UserRegistrationResponse
from src.backend.auth.utils import (
    get_password_hash,
    issue_token_pair,
    verify_password,
    verify_refresh_token,
)
from src.backend.models.user import User, UserStatus

async def register_user(request: UserCreate, db: AsyncSession) -> UserRegistrationResponse:
    """Handle new user registration or completion of an invited user account."""
    existing_user = await _get_user_by_email(db, request.email)
    
    if existing_user:
        return await _handle_existing_user_registration(db, existing_user, request)

    new_user = await _create_and_persist_user(db, request)
    return UserRegistrationResponse(
        message="User registered successfully",
        user_id=new_user.id
    )

async def login_user(request: UserLogin, db: AsyncSession) -> Token:
    """Authenticate a user and return a token pair."""
    user = await _get_active_user_by_email(db, request.email)
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
        
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated or unverified"
        )

    return Token(**issue_token_pair(user))

async def _get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Helper to fetch a user by email, including those who are not active."""
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()


async def _get_active_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Helper to fetch a non-deleted user by email."""
    result = await db.execute(select(User).filter(User.email == email, User.deleted_at.is_(None)))
    return result.scalars().first()

async def _handle_existing_user_registration(db: AsyncSession, user: User, request: UserCreate) -> UserRegistrationResponse:
    """Complete registration for an invited user or raise error if already registered."""
    if user.status != UserStatus.INVITED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    user.name = request.name
    user.password_hash = get_password_hash(request.password)
    user.status = UserStatus.ACTIVE
    user.is_verified = True
    await db.commit()
    
    return UserRegistrationResponse(
        message="User registration completed successfully",
        user_id=user.id
    )

async def _create_and_persist_user(db: AsyncSession, request: UserCreate) -> User:
    """Create a new user record and save to database."""
    new_user = User(
        name=request.name,
        email=request.email,
        password_hash=get_password_hash(request.password),
        status=UserStatus.ACTIVE,
        is_verified=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def refresh_user_token(refresh_token: str, db: AsyncSession) -> Token:
    """Validate a refresh token and return a new token pair."""
    user = await verify_refresh_token(refresh_token, db)
    
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated or unverified"
        )
        
    return Token(**issue_token_pair(user))
