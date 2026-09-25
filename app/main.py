from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.database import engine
from app.routers import ai, auth, profile, resume


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: pre-warm DB connection pool so first request isn't cold."""
    async with engine.connect():
        pass  # forces the pool to create its first connection
    yield
    # Shutdown: dispose engine cleanly
    await engine.dispose()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Compress JSON payloads > 2KB only (avoid wasting CPU on tiny error responses)
app.add_middleware(GZipMiddleware, minimum_size=2048)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire up routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["Candidate Profile"])
app.include_router(resume.router, prefix="/api/v1/resumes", tags=["Resumes"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI Resume Intelligence"])


@app.get("/")
def health_check():
    return {"status": "Server is running"}
