import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_role
from app.models.profile import Resume
from app.models.user import User, UserRole
from app.schemas.ai import ParsedResumeOut, ResumeHealthOut, GenerateHeadlineRequest, GenerateHeadlineResponse
from app.services.ai_service import ai_service
from app.utils.file_parser import extract_text_from_bytes, fetch_resume_bytes

logger = logging.getLogger(__name__)

router = APIRouter()

CandidateUser = Annotated[User, Depends(require_role(UserRole.JOB_SEEKER))]


class DirectTextIn(BaseModel):
    text: str


@router.post(
    "/parse-resume/{resume_id}",
    response_model=ParsedResumeOut,
    status_code=status.HTTP_200_OK,
    summary="Extract structured resume intelligence using Cohere AI",
)
async def parse_resume_endpoint(
    resume_id: int,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Download a candidate's uploaded resume from cloud storage,
    extract raw text, and parse it into an evidence-based structured profile
    using Cohere ClientV2 (command-a-plus-05-2026).
    
    NOTE: This does NOT overwrite the candidate profile in the DB.
    The candidate reviews and accepts/edits changes on the UI.
    """
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found or does not belong to the current user.",
        )

    # 1. Check database cache
    if resume.is_analyzed and resume.parsed_data:
        logger.info("Cache HIT for resume_id=%s. Returning cached AI intelligence.", resume.id)
        return ParsedResumeOut.model_validate(resume.parsed_data)

    # 2. Cache MISS: Download resume file bytes
    try:
        content = await fetch_resume_bytes(resume.file_path)
    except Exception as e:
        logger.error("Failed to fetch resume file bytes: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve resume file from storage: {str(e)}",
        )

    # Extract text from PDF or DOCX
    try:
        extracted_text = extract_text_from_bytes(content, resume.file_type or resume.file_name)
    except Exception as e:
        logger.error("Failed to extract text from resume: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not extract readable text from resume document: {str(e)}",
        )

    if not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The resume document contains no readable text.",
        )

    # Parse using Cohere AI
    parsed_resume = await ai_service.parse_resume_text(extracted_text, resume_id=resume.id)

    # Cache AI results in database
    resume.parsed_data = parsed_resume.model_dump(mode="json")
    resume.health_data = parsed_resume.resume_health.model_dump(mode="json")
    resume.is_analyzed = True
    await db.commit()
    await db.refresh(resume)

    return parsed_resume


@router.post(
    "/resume-health/{resume_id}",
    response_model=ResumeHealthOut,
    status_code=status.HTTP_200_OK,
    summary="Calculate ATS resume health score and suggestions",
)
async def resume_health_endpoint(
    resume_id: int,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Analyze the uploaded resume's ATS health, completeness, structure, and clarity,
    returning a score out of 100 with actionable feedback.
    """
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found or does not belong to the current user.",
        )

    # 1. Check database cache
    if resume.is_analyzed and resume.health_data:
        logger.info("Cache HIT for resume_id=%s. Returning cached ATS health data.", resume.id)
        return ResumeHealthOut.model_validate(resume.health_data)

    try:
        content = await fetch_resume_bytes(resume.file_path)
        extracted_text = extract_text_from_bytes(content, resume.file_type or resume.file_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read resume file: {str(e)}",
        )

    if not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The resume document contains no readable text.",
        )

    parsed_resume = await ai_service.parse_resume_text(extracted_text, resume_id=resume.id)

    # Cache AI results in database
    resume.parsed_data = parsed_resume.model_dump(mode="json")
    resume.health_data = parsed_resume.resume_health.model_dump(mode="json")
    resume.is_analyzed = True
    await db.commit()
    await db.refresh(resume)

    return parsed_resume.resume_health


@router.post(
    "/parse-text",
    response_model=ParsedResumeOut,
    status_code=status.HTTP_200_OK,
    summary="Parse raw resume text directly (developer/preview utility)",
)
async def parse_text_endpoint(
    payload: DirectTextIn,
    current_user: CandidateUser,
):
    """Parse raw resume text directly for live preview and testing."""
    return await ai_service.parse_resume_text(payload.text)


@router.post(
    "/generate-headline",
    response_model=GenerateHeadlineResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a professional headline using AI",
)
async def generate_headline_endpoint(
    payload: GenerateHeadlineRequest,
    current_user: CandidateUser,
):
    """
    Takes the candidate's existing profile data (skills, experience, etc.) and
    uses AI to generate a punchy professional headline.
    """
    headline = await ai_service.generate_professional_headline(payload.profile_data)
    return GenerateHeadlineResponse(headline=headline)
