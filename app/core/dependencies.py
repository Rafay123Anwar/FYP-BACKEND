from collections.abc import AsyncGenerator
from typing import Annotated, Sequence
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import decode_access_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an asynchronous transactional database session scope."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


import time
from collections import OrderedDict
from threading import Lock

# Bounded LRU in-memory user cache (user_id -> (timestamp, User))
# Max 1000 entries prevents memory leak under heavy traffic.
_USER_CACHE: OrderedDict[int, tuple[float, "User"]] = OrderedDict()
_USER_CACHE_LOCK = Lock()
USER_CACHE_TTL_SECONDS = 60.0
_USER_CACHE_MAX = 1000


def invalidate_user_cache(user_id: int | None = None) -> None:
    """Invalidate cached user instance or clear whole cache."""
    with _USER_CACHE_LOCK:
        if user_id is not None:
            _USER_CACHE.pop(user_id, None)
        else:
            _USER_CACHE.clear()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Decode JWT token and fetch active authenticated user with bounded LRU caching."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception

    # Check bounded LRU cache first to avoid WAN DB round-trip
    now = time.time()
    with _USER_CACHE_LOCK:
        cached = _USER_CACHE.get(user_id)
        if cached and (now - cached[0] < USER_CACHE_TTL_SECONDS):
            # Move to end (most-recently-used)
            _USER_CACHE.move_to_end(user_id)
            user = cached[1]
        else:
            user = None

    if user is None:
        # Async DB query — outside lock to avoid blocking event loop
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise credentials_exception
        # Insert into cache with LRU eviction
        with _USER_CACHE_LOCK:
            _USER_CACHE[user_id] = (now, user)
            _USER_CACHE.move_to_end(user_id)
            if len(_USER_CACHE) > _USER_CACHE_MAX:
                _USER_CACHE.popitem(last=False)  # evict oldest

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


class RoleChecker:
    """Role-Based Access Control (RBAC) dependency verifying user roles."""

    def __init__(self, allowed_roles: Sequence[UserRole]):
        self.allowed_roles = set(allowed_roles)

    async def __call__(
        self, current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted: insufficient permissions",
            )
        return current_user


def require_role(*roles: UserRole) -> RoleChecker:
    """Convenience helper to enforce allowed roles on endpoints."""
    return RoleChecker(roles)
