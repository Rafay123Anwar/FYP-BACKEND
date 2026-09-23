import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, timedelta
import pytest
from pydantic import ValidationError
from app.schemas.profile import (
    ProfileCreate,
    ProfileUpdate,
    EducationCreate,
    ExperienceCreate,
)


def test_valid_profile_urls():
    p = ProfileCreate(
        headline="Full Stack Engineer",
        linkedin="https://linkedin.com/in/test-user",
        github="https://github.com/test-user",
    )
    assert p.linkedin == "https://linkedin.com/in/test-user"
    assert p.github == "https://github.com/test-user"

    p_www = ProfileCreate(
        linkedin="https://www.linkedin.com/in/test-user",
        github="https://www.github.com/test-user",
    )
    assert p_www.linkedin == "https://www.linkedin.com/in/test-user"
    assert p_www.github == "https://www.github.com/test-user"

    p_empty = ProfileCreate(linkedin="", github=None)
    assert p_empty.linkedin is None
    assert p_empty.github is None


def test_invalid_linkedin_url():
    with pytest.raises(ValidationError) as exc:
        ProfileCreate(linkedin="http://linkedin.com/in/test")
    assert "LinkedIn URL must start with https://linkedin.com/" in str(exc.value)

    with pytest.raises(ValidationError) as exc2:
        ProfileCreate(linkedin="https://twitter.com/test")
    assert "LinkedIn URL must start with https://linkedin.com/" in str(exc2.value)


def test_invalid_github_url():
    with pytest.raises(ValidationError) as exc:
        ProfileCreate(github="http://github.com/test")
    assert "GitHub URL must start with https://github.com/" in str(exc.value)

    with pytest.raises(ValidationError) as exc2:
        ProfileCreate(github="https://gitlab.com/test")
    assert "GitHub URL must start with https://github.com/" in str(exc2.value)


def test_education_dates():
    # Valid
    e = EducationCreate(
        institution="NUST",
        start_date=date(2018, 9, 1),
        end_date=date(2022, 6, 30),
    )
    assert e.institution == "NUST"

    # End date <= start date
    with pytest.raises(ValidationError) as exc:
        EducationCreate(
            institution="NUST",
            start_date=date(2022, 9, 1),
            end_date=date(2020, 6, 30),
        )
    assert "End date must be after start date" in str(exc.value)

    # Graduation date more than 6 years in future
    future_7_years = date.today() + timedelta(days=365 * 7)
    with pytest.raises(ValidationError) as exc2:
        EducationCreate(
            institution="NUST",
            start_date=date.today(),
            end_date=future_7_years,
        )
    assert "Graduation date cannot be more than 6 years in the future" in str(exc2.value)


def test_experience_dates():
    today = date.today()

    # Valid past experience
    x = ExperienceCreate(
        company="TechLogix",
        job_title="Software Engineer",
        start_date=today - timedelta(days=365),
        end_date=today - timedelta(days=30),
    )
    assert x.company == "TechLogix"

    # Valid currently working here (end_date is None)
    x_curr = ExperienceCreate(
        company="TechLogix",
        job_title="Software Engineer",
        start_date=today - timedelta(days=365),
        end_date=None,
    )
    assert x_curr.end_date is None

    # Start date in future
    with pytest.raises(ValidationError) as exc:
        ExperienceCreate(
            company="TechLogix",
            job_title="Software Engineer",
            start_date=today + timedelta(days=30),
        )
    assert "Start date cannot be in the future" in str(exc.value)

    # End date before start date
    with pytest.raises(ValidationError) as exc2:
        ExperienceCreate(
            company="TechLogix",
            job_title="Software Engineer",
            start_date=today - timedelta(days=100),
            end_date=today - timedelta(days=200),
        )
    assert "End date must be on or after start date" in str(exc2.value)


if __name__ == "__main__":
    test_valid_profile_urls()
    test_invalid_linkedin_url()
    test_invalid_github_url()
    test_education_dates()
    test_experience_dates()
    print("ALL PYDANTIC VALIDATION TESTS PASSED!")
