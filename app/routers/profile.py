import re
from datetime import date
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ai import ParsedResumeOut

from app.core.dependencies import get_db, require_role
from app.models.profile import (
    CandidateSkill,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
)
from app.models.user import User, UserRole
from app.schemas.profile import (
    CandidateFullProfileOut,
    CandidateSkillOut,
    EducationCreate,
    EducationOut,
    EducationUpdate,
    ExperienceCreate,
    ExperienceOut,
    ExperienceUpdate,
    ProfileCreate,
    ProfileOut,
    ProfileUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    SkillCreate,
)

router = APIRouter()

# Dependency enforcing JOB_SEEKER role for candidate profile routes
CandidateUser = Annotated[User, Depends(require_role(UserRole.JOB_SEEKER))]


# ============================================================================
# 1. Profile Endpoints (GET / and PUT /)
# ============================================================================

@router.get("/", response_model=ProfileOut)
async def get_profile(
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve the profile details of the current candidate."""
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create or update your profile.",
        )
    return profile


@router.put("/", response_model=ProfileOut)
async def upsert_profile(
    profile_in: ProfileUpdate,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create or update the candidate's profile with explicit field updates."""
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()

    update_data = profile_in.model_dump(exclude_unset=True)

    if profile is None:
        profile = Profile(
            user_id=current_user.id,
            headline=update_data.get("headline"),
            summary=update_data.get("summary"),
            location=update_data.get("location"),
            phone=update_data.get("phone"),
            website=update_data.get("website"),
            linkedin=update_data.get("linkedin"),
            github=update_data.get("github"),
        )
        db.add(profile)
    else:
        # Explicitly update all provided fields from the ProfileUpdate schema
        allowed_fields = ("headline", "summary", "location", "phone", "website", "linkedin", "github")
        for field in allowed_fields:
            if field in update_data:
                setattr(profile, field, update_data[field])

    await db.commit()
    await db.refresh(profile)
    return profile


# ============================================================================
# 2. Education Endpoints
# ============================================================================

@router.get("/education", response_model=list[EducationOut])
async def list_educations(
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all education records for the current candidate."""
    result = await db.execute(
        select(Education)
        .where(Education.user_id == current_user.id)
        .order_by(Education.start_date.desc().nullslast())
    )
    return result.scalars().all()


@router.post("/education", response_model=EducationOut, status_code=status.HTTP_201_CREATED)
async def create_education(
    education_in: EducationCreate,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a new education record."""
    education = Education(user_id=current_user.id, **education_in.model_dump())
    db.add(education)
    await db.commit()
    await db.refresh(education)
    return education


@router.put("/education/{id}", response_model=EducationOut)
async def update_education(
    id: int,
    education_in: EducationUpdate,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing education record owned by the candidate."""
    result = await db.execute(
        select(Education).where(Education.id == id, Education.user_id == current_user.id)
    )
    education = result.scalar_one_or_none()
    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found",
        )

    for field, value in education_in.model_dump(exclude_unset=True).items():
        setattr(education, field, value)

    await db.commit()
    await db.refresh(education)
    return education


@router.delete("/education/{id}", status_code=status.HTTP_200_OK)
async def delete_education(
    id: int,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete an education record owned by the candidate."""
    result = await db.execute(
        select(Education).where(Education.id == id, Education.user_id == current_user.id)
    )
    education = result.scalar_one_or_none()
    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found",
        )

    await db.delete(education)
    await db.commit()
    return {"message": "Education record deleted successfully"}


# ============================================================================
# 3. Experience Endpoints
# ============================================================================

@router.get("/experience", response_model=list[ExperienceOut])
async def list_experiences(
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all experience records for the current candidate."""
    result = await db.execute(
        select(Experience)
        .where(Experience.user_id == current_user.id)
        .order_by(Experience.start_date.desc().nullslast())
    )
    return result.scalars().all()


@router.post("/experience", response_model=ExperienceOut, status_code=status.HTTP_201_CREATED)
async def create_experience(
    experience_in: ExperienceCreate,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a new experience record."""
    experience = Experience(user_id=current_user.id, **experience_in.model_dump())
    db.add(experience)
    await db.commit()
    await db.refresh(experience)
    return experience


@router.put("/experience/{id}", response_model=ExperienceOut)
async def update_experience(
    id: int,
    experience_in: ExperienceUpdate,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing experience record owned by the candidate."""
    result = await db.execute(
        select(Experience).where(Experience.id == id, Experience.user_id == current_user.id)
    )
    experience = result.scalar_one_or_none()
    if not experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience record not found",
        )

    for field, value in experience_in.model_dump(exclude_unset=True).items():
        setattr(experience, field, value)

    await db.commit()
    await db.refresh(experience)
    return experience


@router.delete("/experience/{id}", status_code=status.HTTP_200_OK)
async def delete_experience(
    id: int,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete an experience record owned by the candidate."""
    result = await db.execute(
        select(Experience).where(Experience.id == id, Experience.user_id == current_user.id)
    )
    experience = result.scalar_one_or_none()
    if not experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience record not found",
        )

    await db.delete(experience)
    await db.commit()
    return {"message": "Experience record deleted successfully"}


# ============================================================================
# 4. Skills Endpoints (POST /skills and DELETE /skills/{id})
# ============================================================================

@router.get("/skills", response_model=list[CandidateSkillOut])
async def list_skills(
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all skills assigned to the current candidate."""
    result = await db.execute(
        select(CandidateSkill).where(CandidateSkill.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/skills", response_model=CandidateSkillOut, status_code=status.HTTP_201_CREATED)
async def add_skill(
    skill_in: SkillCreate,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a skill to the candidate's profile (creates skill in catalog if new)."""
    skill_name = skill_in.name.strip()
    if not skill_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill name cannot be empty",
        )

    # Find or create skill in global catalog (case-insensitive)
    result = await db.execute(select(Skill).where(Skill.name.ilike(skill_name)))
    skill = result.scalar_one_or_none()

    if not skill:
        skill = Skill(name=skill_name)
        db.add(skill)
        await db.flush()

    # Check if already added to candidate profile
    existing_link = await db.execute(
        select(CandidateSkill).where(
            CandidateSkill.user_id == current_user.id,
            CandidateSkill.skill_id == skill.id,
        )
    )
    candidate_skill = existing_link.scalar_one_or_none()
    if candidate_skill:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill already added to your profile",
        )

    candidate_skill = CandidateSkill(user_id=current_user.id, skill_id=skill.id)
    db.add(candidate_skill)
    await db.commit()
    await db.refresh(candidate_skill)
    return candidate_skill


@router.delete("/skills/{id}", status_code=status.HTTP_200_OK)
async def delete_skill(
    id: int,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove a skill from the candidate's profile (accepts candidate_skill id or skill_id)."""
    result = await db.execute(
        select(CandidateSkill).where(
            CandidateSkill.user_id == current_user.id,
            or_(CandidateSkill.id == id, CandidateSkill.skill_id == id),
        )
    )
    candidate_skill = result.scalar_one_or_none()
    if not candidate_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found on candidate profile",
        )

    await db.delete(candidate_skill)
    await db.commit()
    return {"message": "Skill removed from profile successfully"}


# ============================================================================
# 5. Project Endpoints
# ============================================================================

@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all projects for the current candidate."""
    result = await db.execute(
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
    )
    return result.scalars().all()


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a new project record."""
    project = Project(user_id=current_user.id, **project_in.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.put("/projects/{id}", response_model=ProjectOut)
async def update_project(
    id: int,
    project_in: ProjectUpdate,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing project record owned by the candidate."""
    result = await db.execute(
        select(Project).where(Project.id == id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project record not found",
        )

    for field, value in project_in.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/projects/{id}", status_code=status.HTTP_200_OK)
async def delete_project(
    id: int,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a project record owned by the candidate."""
    result = await db.execute(
        select(Project).where(Project.id == id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project record not found",
        )

    await db.delete(project)
    await db.commit()
    return {"message": "Project record deleted successfully"}


# ============================================================================
# 6. Full Profile View (Aggregated - High Performance Single Trip)
# ============================================================================

@router.get("/full", response_model=CandidateFullProfileOut)
async def get_full_candidate_profile(
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve candidate's complete portfolio profile via a single-trip JSON aggregation query."""
    q = text("""
        SELECT json_build_object(
            'profile', (SELECT to_jsonb(p) FROM profiles p WHERE p.user_id = :uid),
            'educations', COALESCE((SELECT jsonb_agg(to_jsonb(e) ORDER BY e.start_date DESC NULLS LAST) FROM educations e WHERE e.user_id = :uid), '[]'::jsonb),
            'experiences', COALESCE((SELECT jsonb_agg(to_jsonb(x) ORDER BY x.start_date DESC NULLS LAST) FROM experiences x WHERE x.user_id = :uid), '[]'::jsonb),
            'skills', COALESCE((
                SELECT jsonb_agg(jsonb_build_object('id', cs.id, 'user_id', cs.user_id, 'skill_id', cs.skill_id, 'skill', to_jsonb(s)))
                FROM candidate_skills cs JOIN skills s ON s.id = cs.skill_id WHERE cs.user_id = :uid
            ), '[]'::jsonb),
            'projects', COALESCE((SELECT jsonb_agg(to_jsonb(pr) ORDER BY pr.created_at DESC) FROM projects pr WHERE pr.user_id = :uid), '[]'::jsonb),
            'resumes', COALESCE((SELECT jsonb_agg(to_jsonb(r) ORDER BY r.uploaded_at DESC) FROM resumes r WHERE r.user_id = :uid), '[]'::jsonb)
        )
    """)
    res = await db.execute(q, {"uid": current_user.id})
    data = res.scalar() or {}
    return CandidateFullProfileOut.model_validate(data)


# ============================================================================
# 7. AI Resume Intelligence Sync (Overwrite Profile with User Consent)
# ============================================================================

def parse_flexible_date(date_str: Optional[str]) -> Optional[date]:
    """Parse various resume date string formats into standard Python date."""
    if not date_str or not isinstance(date_str, str):
        return None
    s = date_str.strip()
    if not s or s.lower() in {"present", "current", "now"}:
        return None

    # Try YYYY-MM-DD
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # Try YYYY-MM
    m = re.search(r"(\d{4})-(\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), 1)
        except ValueError:
            pass

    # Try Month Year (e.g. May 2022, September 2023)
    month_names = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    m = re.search(r"\b([A-Za-z]{3,9})\s+(\d{4})\b", s)
    if m:
        m_name = m.group(1)[:3].lower()
        if m_name in month_names:
            try:
                return date(int(m.group(2)), month_names[m_name], 1)
            except ValueError:
                pass

    # Try Month/Year or MM/YYYY
    m = re.search(r"(\d{1,2})/(\d{4})", s)
    if m:
        try:
            return date(int(m.group(2)), int(m.group(1)), 1)
        except ValueError:
            pass

    # Try YYYY/MM/DD or YYYY/MM
    m = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # Try 4-digit year e.g. 2022
    m = re.search(r"\b(19\d{2}|20\d{2})\b", s)
    if m:
        return date(int(m.group(1)), 1, 1)

    return None


def normalize_profile_url(url: Optional[str], domain: str) -> Optional[str]:
    """Ensure raw resume URL strings have valid https:// protocol and match the expected domain."""
    if not url or not isinstance(url, str):
        return None
    clean = url.strip()
    if not clean:
        return None
    # Strip protocol and www. if present to evaluate canonical path
    clean = re.sub(r"^https?:\/\/", "", clean, flags=re.I)
    clean = re.sub(r"^www\.", "", clean, flags=re.I)
    if clean.lower().startswith(f"{domain}/") or re.match(rf"^(?:[a-zA-Z0-9-]+\.)?{re.escape(domain)}\/.*$", clean, flags=re.I):
        return f"https://{clean}"
    return None


@router.post(
    "/sync-ai-data",
    status_code=status.HTTP_200_OK,
    summary="Bulk synchronize candidate profile with AI parsed intelligence",
)
async def sync_ai_data(
    payload: ParsedResumeOut,
    current_user: CandidateUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Explicitly delete current user's existing Education and Experience records,
    and bulk-insert newly verified education, experience, and categorized skills.
    Also update profile summary and contact links if present without overwriting
    manually entered details with null/empty values.
    """
    # 1. Update / Create Profile
    prof_res = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = prof_res.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    # Preserve manually entered basic info: only update if AI extracted a valid non-empty string
    summary = getattr(payload, "professional_summary", None)
    if summary and isinstance(summary, str) and summary.strip():
        profile.summary = summary.strip()

    contact = getattr(payload, "contact", None)
    if contact:
        loc = getattr(contact, "location", None)
        if loc and isinstance(loc, str) and loc.strip() and loc.strip().lower() not in ("none", "n/a", "null"):
            profile.location = loc.strip()

        phone = getattr(contact, "phone", None)
        if phone and isinstance(phone, str) and phone.strip() and phone.strip().lower() not in ("none", "n/a", "null"):
            profile.phone = phone.strip()

        li = getattr(contact, "linkedin", None)
        if li and isinstance(li, str) and li.strip():
            normalized_li = normalize_profile_url(li, "linkedin.com")
            if normalized_li:
                profile.linkedin = normalized_li

        gh = getattr(contact, "github", None)
        if gh and isinstance(gh, str) and gh.strip():
            normalized_gh = normalize_profile_url(gh, "github.com")
            if normalized_gh:
                profile.github = normalized_gh

    # 2. Explicitly delete existing Education records
    await db.execute(delete(Education).where(Education.user_id == current_user.id))

    # 3. Explicitly delete existing Experience records
    await db.execute(delete(Experience).where(Experience.user_id == current_user.id))

    # 4. Insert new Education records
    for edu in payload.education:
        new_edu = Education(
            user_id=current_user.id,
            institution=edu.institution or "Educational Institution",
            degree=edu.degree,
            field=edu.degree,
            start_date=parse_flexible_date(edu.start_date),
            end_date=parse_flexible_date(edu.end_date),
            description=f"CGPA: {edu.cgpa}" if edu.cgpa else (edu.evidence or None),
        )
        db.add(new_edu)

    # 5. Insert new Experience records
    for exp in payload.experience:
        desc_parts = []
        if exp.responsibilities:
            desc_parts.extend(exp.responsibilities)
        if exp.technologies:
            desc_parts.append(f"Technologies: {', '.join(exp.technologies)}")
        description = "\n".join(desc_parts) if desc_parts else (exp.evidence or None)

        new_exp = Experience(
            user_id=current_user.id,
            company=exp.company or "Company",
            job_title=exp.job_title or "Role",
            start_date=parse_flexible_date(exp.start_date),
            end_date=parse_flexible_date(exp.end_date),
            description=description,
        )
        db.add(new_exp)

    # 6. Synchronize Skills (find-or-create in Skill catalog)
    all_skill_names: set[str] = set()
    for cat_list in [
        payload.skills.technical_foundation,
        payload.skills.process_and_automation,
        payload.skills.project_and_product_coordination,
        payload.skills.data_informed_decision_making,
        payload.skills.other,
    ]:
        for s in cat_list:
            clean = s.strip()
            if clean and len(clean) <= 100:
                all_skill_names.add(clean)

    if all_skill_names:
        # Delete existing candidate skills to avoid duplicates
        await db.execute(delete(CandidateSkill).where(CandidateSkill.user_id == current_user.id))

        for name in all_skill_names:
            skill_res = await db.execute(select(Skill).where(func.lower(Skill.name) == name.lower()))
            skill = skill_res.scalar_one_or_none()
            if not skill:
                skill = Skill(name=name)
                db.add(skill)
                await db.flush()

            cand_skill = CandidateSkill(user_id=current_user.id, skill_id=skill.id)
            db.add(cand_skill)

    await db.commit()
    return {"status": "success", "message": "Profile successfully synchronized with AI extracted data."}
