import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# Dedicated thread pool for bcrypt so it doesn't starve the default asyncio
# thread pool under high concurrency (100 concurrent logins).
_BCRYPT_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="bcrypt")

# bcrypt rounds=10 ≈ 100ms/hash (rounds=12 ≈ 300ms). For 100 concurrent logins,
# this means 10s of aggregate wait with 8 threads vs 37s with rounds=12.
_BCRYPT_ROUNDS = 10


def _sync_verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def _sync_get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored bcrypt hash using a dedicated thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_BCRYPT_POOL, _sync_verify_password, plain_password, hashed_password)


async def get_password_hash(password: str) -> str:
    """Generate a bcrypt password hash using a dedicated thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_BCRYPT_POOL, _sync_get_password_hash, password)


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
