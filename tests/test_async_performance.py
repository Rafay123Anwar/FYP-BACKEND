"""Performance verification tests for asynchronous hashing, Cohere V2, and payload compression."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import pytest
import cohere
from app.core.security import get_password_hash, verify_password
from app.services.ai_service import ai_service
from app.main import app
from fastapi.middleware.gzip import GZipMiddleware


@pytest.mark.asyncio
async def test_async_password_hashing():
    """Verify that password hashing and verification run as non-blocking async coroutines."""
    plain = "SuperSecretPassword123!"
    # Execute multiple password hashes concurrently in parallel tasks
    hashes = await asyncio.gather(
        get_password_hash(plain),
        get_password_hash(plain),
        get_password_hash(plain),
    )
    assert len(hashes) == 3
    for h in hashes:
        assert h.startswith("$2b$")
        is_valid = await verify_password(plain, h)
        assert is_valid is True

    is_invalid = await verify_password("WrongPassword!", hashes[0])
    assert is_invalid is False


def test_cohere_async_client_initialized():
    """Verify that AIService initializes and uses cohere.AsyncClientV2."""
    client = ai_service.get_client()
    assert isinstance(client, cohere.AsyncClientV2)


def test_gzip_middleware_registered():
    """Verify GZipMiddleware is registered in FastAPI app for payload compression."""
    middleware_classes = [m.cls for m in app.user_middleware]
    assert GZipMiddleware in middleware_classes


from httpx import ASGITransport, AsyncClient
from app.core.database import engine

@pytest.mark.asyncio
async def test_auth_endpoints_async():
    """Verify that auth endpoints execute asynchronously via ASGI transport."""
    await engine.dispose()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "Password123!"},
        )
        assert res.status_code == 401
        assert res.json()["detail"] == "Incorrect email or password"
    await engine.dispose()
