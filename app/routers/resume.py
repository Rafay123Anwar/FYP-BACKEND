import uuid
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_role
from app.models.profile import Resume
from app.models.user import User, UserRole
from app.schemas.profile import ResumeOut
from app.utils.supabase_client import supabase_client

router = APIRouter()

CandidateUser = Annotated[User, Depends(require_role(UserRole.JOB_SEEKER))]

BUCKET_NAME = "resumes"
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/octet-stream",  # Fallback for binary uploads
}


def extract_storage_path(url_or_path: str, bucket: str = BUCKET_NAME) -> str:
    """Extract relative object path in bucket from a full public Supabase URL or stored path."""
    delimiter = f"/{bucket}/"
    if delimiter in url_or_path:
        return url_or_path.split(delimiter, 1)[1]
    return url_or_path


@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.JOB_SEEKER)),
    db: AsyncSession = Depends(get_db),
):
    """Upload a candidate resume to the Supabase Storage 'resumes' bucket."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format: {file_ext}. Only PDF and DOCX files are allowed.",
        )

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MIME type: {file.content_type}. Only PDF and DOCX files are allowed.",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file cannot be empty",
        )

    # Determine explicit MIME type for Supabase storage header
    if file_ext == ".pdf":
        content_type = "application/pdf"
    elif file_ext == ".docx":
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        content_type = file.content_type or "application/octet-stream"

    # Generate unique storage path: {user_id}/{uuid4}_{filename}
    clean_original_name = Path(file.filename).name.replace(" ", "_")
    storage_path = f"{current_user.id}/{uuid.uuid4().hex}_{clean_original_name}"

    # Upload to Supabase Storage bucket
    try:
        supabase_client.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type, "upsert": "false"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload resume to cloud storage: {str(e)}",
        )

    # Get public URL
    public_url = supabase_client.storage.from_(BUCKET_NAME).get_public_url(storage_path)

    # Persist metadata in database
    resume = Resume(
        user_id=current_user.id,
        file_name=file.filename,
        file_path=public_url,
        file_type=file_ext.lstrip("."),
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return resume


@router.get("/", response_model=list[ResumeOut])
async def list_resumes(
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all uploaded resumes belonging to the current user."""
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.uploaded_at.desc())
    )
    return result.scalars().all()


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_resume(
    id: int,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a resume from Supabase Storage and remove its DB record."""
    result = await db.execute(
        select(Resume).where(Resume.id == id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    # Extract storage path and delete from Supabase bucket
    storage_path = extract_storage_path(resume.file_path, bucket=BUCKET_NAME)
    try:
        supabase_client.storage.from_(BUCKET_NAME).remove([storage_path])
    except Exception:
        # Proceed with DB deletion even if storage deletion encounters an issue
        pass

    await db.delete(resume)
    await db.commit()
    return {"message": "Resume deleted successfully"}
