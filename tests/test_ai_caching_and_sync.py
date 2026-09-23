import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from app.models.profile import Resume
from app.schemas.profile import ResumeOut
from app.schemas.ai import ParsedResumeOut, ResumeHealthOut
from app.routers.profile import parse_flexible_date


def test_resume_model_ai_columns():
    """Verify Resume model has is_analyzed, parsed_data, and health_data columns."""
    assert hasattr(Resume, "is_analyzed")
    assert hasattr(Resume, "parsed_data")
    assert hasattr(Resume, "health_data")

    # Verify column defaults
    r = Resume(user_id=1, file_name="resume.pdf", file_path="http://storage/resume.pdf")
    assert r.is_analyzed is False or r.is_analyzed is None


def test_resume_out_schema():
    """Verify ResumeOut schema handles new AI fields."""
    sample_data = {
        "id": 1,
        "user_id": 1,
        "file_name": "resume.pdf",
        "file_path": "https://storage/resume.pdf",
        "file_type": "pdf",
        "uploaded_at": "2026-09-23T12:00:00",
        "is_analyzed": True,
        "parsed_data": {"personal_info": {"full_name": "Jane Doe"}},
        "health_data": {"overall_resume_health_score": 90},
    }
    schema = ResumeOut.model_validate(sample_data)
    assert schema.is_analyzed is True
    assert schema.parsed_data["personal_info"]["full_name"] == "Jane Doe"
    assert schema.health_data["overall_resume_health_score"] == 90


def test_parse_flexible_date():
    """Verify parse_flexible_date parses YYYY-MM-DD, YYYY-MM, YYYY, and handles fallbacks."""
    assert parse_flexible_date("2022-05-15") == date(2022, 5, 15)
    assert parse_flexible_date("2022-05") == date(2022, 5, 1)
    assert parse_flexible_date("2022") == date(2022, 1, 1)
    assert parse_flexible_date("May 2022") == date(2022, 5, 1)
    assert parse_flexible_date("2022/08/10") == date(2022, 8, 10)
    assert parse_flexible_date(None) is None
    assert parse_flexible_date("") is None
    assert parse_flexible_date("Present") is None
    assert parse_flexible_date("Current") is None


import pytest
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

@pytest.mark.asyncio
async def test_db_has_resume_ai_columns():
    """Verify that is_analyzed, parsed_data, and health_data exist in the DB table."""
    async with AsyncSessionLocal() as session:
        query = text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'resumes';"
        )
        result = await session.execute(query)
        columns = [row[0] for row in result.fetchall()]
        assert "is_analyzed" in columns
        assert "parsed_data" in columns
        assert "health_data" in columns


def test_profile_url_auto_normalization():
    """Verify that domain-only LinkedIn and GitHub URLs auto-prefix with https://."""
    from app.schemas.profile import ProfileCreate, ProfileOut
    
    p = ProfileCreate(
        headline="AI Engineer",
        linkedin="linkedin.com/in/muhammad-rafay-anwar-308666296",
        github="github.com/muhammadrafay",
    )
    assert p.linkedin == "https://linkedin.com/in/muhammad-rafay-anwar-308666296"
    assert p.github == "https://github.com/muhammadrafay"

    p_www = ProfileCreate(
        linkedin="www.linkedin.com/in/muhammad-rafay-anwar-308666296",
        github="www.github.com/muhammadrafay",
    )
    assert p_www.linkedin == "https://www.linkedin.com/in/muhammad-rafay-anwar-308666296"
    assert p_www.github == "https://www.github.com/muhammadrafay"


