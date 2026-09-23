from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.routers import ai, auth, profile, resume

app = FastAPI(title=settings.PROJECT_NAME)

# High-concurrency performance: compress JSON payloads > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
