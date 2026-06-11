import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Dict, Any, Optional

from src.backend.config import Config
from src.backend.db.database import get_db
from src.backend.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_pwd = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_pwd.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

def build_token_payload(user: User) -> Dict[str, str]:
    return {"user_id": str(user.id), "email": user.email}

def issue_token_pair(user: User) -> Dict[str, str]:
    token_data = build_token_payload(user)
    return {
        "access_token": create_access_token(data=token_data),
        "refresh_token": create_refresh_token(data=token_data),
        "token_type": "bearer",
        "name": user.name,
        "user_id": str(user.id)
    }

def create_access_token(data: Dict[str, Any]) -> str:
    return _generate_token(data, Config.ACCESS_TOKEN_EXPIRE_MINUTES, Config.ACCESS_SECRET_KEY, is_minutes=True)

def create_refresh_token(data: Dict[str, Any]) -> str:
    return _generate_token(data, Config.REFRESH_TOKEN_EXPIRE_DAYS, Config.REFRESH_SECRET_KEY, is_minutes=False)

def _generate_token(data: Dict[str, Any], expiry: int, secret: str, is_minutes: bool) -> str:
    to_encode = data.copy()
    delta = timedelta(minutes=expiry) if is_minutes else timedelta(days=expiry)
    to_encode.update({"exp": datetime.utcnow() + delta})
    return jwt.encode(to_encode, secret, algorithm=Config.ALGORITHM)

async def verify_refresh_token(token: str, db: AsyncSession) -> User:
    payload = _decode_token(token, Config.REFRESH_SECRET_KEY)
    return await _get_user_from_payload(payload, db)

async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    payload = _decode_token(token.credentials, Config.ACCESS_SECRET_KEY)
    return await _get_user_from_payload(payload, db)

def _decode_token(token: str, secret: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, secret, algorithms=[Config.ALGORITHM])
        if "user_id" not in payload:
            raise ValueError("Invalid payload")
        return payload
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def _get_user_from_payload(payload: Dict[str, Any], db: AsyncSession) -> User:
    user_id = UUID(payload["user_id"])
    result = await db.execute(select(User).filter(User.id == user_id, User.deleted_at.is_(None)))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def get_ws_user(token: str, db: AsyncSession) -> User:
    """Authenticate a WebSocket connection via token query param."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = _decode_token(token, Config.ACCESS_SECRET_KEY)
    return await _get_user_from_payload(payload, db)
