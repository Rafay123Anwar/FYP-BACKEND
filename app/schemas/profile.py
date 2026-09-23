import re
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------- Profile Schemas ----------------
class ProfileBase(BaseModel):
    headline: Optional[str] = Field(None, max_length=255, examples=["Senior Python Developer"])
    summary: Optional[str] = Field(None, examples=["Experienced backend software engineer specializing in FastAPI and scalable architectures."])
    location: Optional[str] = Field(None, max_length=255, examples=["Karachi, Pakistan"])
    phone: Optional[str] = Field(None, max_length=50, examples=["+92-300-1234567"])
    website: Optional[str] = Field(None, max_length=255, examples=["https://myportfolio.dev"])
    linkedin: Optional[str] = Field(None, max_length=255, examples=["https://linkedin.com/in/johndoe"])
    github: Optional[str] = Field(None, max_length=255, examples=["https://github.com/johndoe"])

    @field_validator("linkedin", mode="before")
    @classmethod
    def validate_linkedin(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = str(v).strip()
        if not clean:
            return None
        if not clean.lower().startswith("http://") and not clean.lower().startswith("https://"):
            clean = "https://" + clean
        elif clean.lower().startswith("http://"):
            clean = "https://" + clean[7:]
        if not re.match(r"^https:\/\/(?:[a-zA-Z0-9-]+\.)?linkedin\.com\/.*$", clean, flags=re.I):
            raise ValueError("LinkedIn URL must be a valid profile link (e.g. https://linkedin.com/in/username)")
        return clean

    @field_validator("github", mode="before")
    @classmethod
    def validate_github(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = str(v).strip()
        if not clean:
            return None
        if not clean.lower().startswith("http://") and not clean.lower().startswith("https://"):
            clean = "https://" + clean
        elif clean.lower().startswith("http://"):
            clean = "https://" + clean[7:]
        if not re.match(r"^https:\/\/(?:www\.)?github\.com\/.*$", clean, flags=re.I):
            raise ValueError("GitHub URL must be a valid profile link (e.g. https://github.com/username)")
        return clean


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileOut(ProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Education Schemas ----------------
class EducationBase(BaseModel):
    institution: str = Field(..., min_length=1, max_length=255, examples=["FAST - National University of Computer and Emerging Sciences"])
    degree: Optional[str] = Field(None, max_length=255, examples=["Bachelor of Science"])
    field: Optional[str] = Field(None, max_length=255, examples=["Computer Science"])
    start_date: Optional[date] = Field(None, examples=["2018-09-01"])
    end_date: Optional[date] = Field(None, examples=["2022-05-31"])
    description: Optional[str] = Field(None, examples=["Focused on distributed systems and database architectures."])

    @model_validator(mode="after")
    def validate_education_dates(self) -> "EducationBase":
        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValueError("End date must be after start date.")
        if self.end_date:
            max_future = date.today().replace(year=date.today().year + 6)
            if self.end_date > max_future:
                raise ValueError("Graduation date cannot be more than 6 years in the future.")
        return self


class EducationCreate(EducationBase):
    pass


class EducationUpdate(BaseModel):
    institution: Optional[str] = Field(None, min_length=1, max_length=255)
    degree: Optional[str] = Field(None, max_length=255)
    field: Optional[str] = Field(None, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def validate_education_update_dates(self) -> "EducationUpdate":
        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValueError("End date must be after start date.")
        if self.end_date:
            max_future = date.today().replace(year=date.today().year + 6)
            if self.end_date > max_future:
                raise ValueError("Graduation date cannot be more than 6 years in the future.")
        return self


class EducationOut(EducationBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Experience Schemas ----------------
class ExperienceBase(BaseModel):
    company: str = Field(..., min_length=1, max_length=255, examples=["TechLogix"])
    job_title: str = Field(..., min_length=1, max_length=255, examples=["Software Engineer"])
    start_date: Optional[date] = Field(None, examples=["2022-06-01"])
    end_date: Optional[date] = Field(None, examples=["2024-08-31"])
    description: Optional[str] = Field(None, examples=["Designed and maintained REST APIs using FastAPI and PostgreSQL."])

    @model_validator(mode="after")
    def validate_experience_dates(self) -> "ExperienceBase":
        today = date.today()
        if self.start_date and self.start_date > today:
            raise ValueError("Start date cannot be in the future.")
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("End date must be on or after start date.")
            if self.end_date > today:
                raise ValueError("End date cannot be in the future for past experience.")
        return self


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceUpdate(BaseModel):
    company: Optional[str] = Field(None, min_length=1, max_length=255)
    job_title: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def validate_experience_update_dates(self) -> "ExperienceUpdate":
        today = date.today()
        if self.start_date and self.start_date > today:
            raise ValueError("Start date cannot be in the future.")
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("End date must be on or after start date.")
            if self.end_date > today:
                raise ValueError("End date cannot be in the future for past experience.")
        return self


class ExperienceOut(ExperienceBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Skill Schemas ----------------
class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Python"])


class SkillOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class CandidateSkillOut(BaseModel):
    id: int
    user_id: int
    skill_id: int
    skill: SkillOut

    model_config = ConfigDict(from_attributes=True)


# ---------------- Project Schemas ----------------
class ProjectBase(BaseModel):
    title: str = Field(..., max_length=255, examples=["Distributed Task Queue"])
    description: Optional[str] = Field(None, examples=["High performance message broker integration."])
    technologies: Optional[str] = Field(None, max_length=255, examples=["Python, Redis, Docker"])
    url: Optional[str] = Field(None, max_length=255, examples=["https://github.com/johndoe/task-queue"])


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    technologies: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=255)


class ProjectOut(ProjectBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Resume Schemas ----------------
class ResumeOut(BaseModel):
    id: int
    user_id: int
    file_name: str
    file_path: str
    file_url: Optional[str] = None
    file_type: str
    uploaded_at: datetime
    is_analyzed: bool = False
    parsed_data: Optional[dict] = None
    health_data: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context) -> None:
        if not self.file_url:
            self.file_url = self.file_path


# ---------------- Full Candidate Profile ----------------
class CandidateFullProfileOut(BaseModel):
    profile: Optional[ProfileOut] = None
    educations: list[EducationOut] = []
    experiences: list[ExperienceOut] = []
    skills: list[CandidateSkillOut] = []
    projects: list[ProjectOut] = []
    resumes: list[ResumeOut] = []

    model_config = ConfigDict(from_attributes=True)
