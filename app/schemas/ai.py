from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ContactInfo(BaseModel):
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None


class SkillsOut(BaseModel):
    project_and_product_coordination: list[str] = Field(default_factory=list)
    process_and_automation: list[str] = Field(default_factory=list)
    technical_foundation: list[str] = Field(default_factory=list)
    data_informed_decision_making: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)

    @field_validator(
        "project_and_product_coordination",
        "process_and_automation",
        "technical_foundation",
        "data_informed_decision_making",
        "other",
        mode="before",
    )
    @classmethod
    def coerce_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class ParsedProject(BaseModel):
    name: str = ""
    technologies: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    evidence: Optional[str] = None

    @field_validator("technologies", mode="before")
    @classmethod
    def coerce_tech(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class ParsedExperience(BaseModel):
    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    responsibilities: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    evidence: Optional[str] = None

    @field_validator("responsibilities", "technologies", mode="before")
    @classmethod
    def coerce_exp_lists(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class ParsedEducation(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    cgpa: Optional[str] = None
    evidence: Optional[str] = None


class ParsedCertification(BaseModel):
    name: str = ""
    provider: Optional[str] = None
    date: Optional[str] = None
    evidence: Optional[str] = None


class ParsedAchievement(BaseModel):
    title: str = ""
    description: Optional[str] = None
    evidence: Optional[str] = None


class ParsedLanguage(BaseModel):
    language: str = ""
    proficiency: Optional[str] = None
    evidence: Optional[str] = None


class ResumeUnderstanding(BaseModel):
    candidate_profile: Optional[str] = None
    technical_profile: Optional[str] = None
    project_profile: Optional[str] = None
    experience_profile: Optional[str] = None
    education_profile: Optional[str] = None
    certification_profile: Optional[str] = None
    language_profile: Optional[str] = None


class ResumeStructure(BaseModel):
    present_sections: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    incomplete_sections: list[str] = Field(default_factory=list)

    @field_validator("present_sections", "missing_sections", "incomplete_sections", mode="before")
    @classmethod
    def coerce_sections(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class ResumeHealthOut(BaseModel):
    completeness_score: int = 0
    contact_information_score: int = 0
    section_structure_score: int = 0
    skills_clarity_score: int = 0
    project_detail_score: int = 0
    education_detail_score: int = 0
    experience_detail_score: int = 0
    overall_resume_health_score: int = 0
    reasons: list[str] = Field(default_factory=list)

    @field_validator(
        "completeness_score",
        "contact_information_score",
        "section_structure_score",
        "skills_clarity_score",
        "project_detail_score",
        "education_detail_score",
        "experience_detail_score",
        "overall_resume_health_score",
        mode="before",
    )
    @classmethod
    def coerce_scores(cls, v):
        if v is None:
            return 0
        try:
            return round(float(v))
        except (ValueError, TypeError):
            return 0


class ParsedResumeOut(BaseModel):
    resume_id: Optional[int] = None
    name: Optional[str] = None
    contact: ContactInfo = Field(default_factory=ContactInfo)
    professional_summary: Optional[str] = None
    skills: SkillsOut = Field(default_factory=SkillsOut)
    projects: list[ParsedProject] = Field(default_factory=list)
    experience: list[ParsedExperience] = Field(default_factory=list)
    education: list[ParsedEducation] = Field(default_factory=list)
    certifications: list[ParsedCertification] = Field(default_factory=list)
    achievements: list[ParsedAchievement] = Field(default_factory=list)
    languages: list[ParsedLanguage] = Field(default_factory=list)
    resume_understanding: ResumeUnderstanding = Field(default_factory=ResumeUnderstanding)
    resume_structure: ResumeStructure = Field(default_factory=ResumeStructure)
    resume_health: ResumeHealthOut = Field(default_factory=ResumeHealthOut)

    @field_validator(
        "projects",
        "experience",
        "education",
        "certifications",
        "achievements",
        "languages",
        mode="before",
    )
    @classmethod
    def coerce_record_lists(cls, v):
        if v is None:
            return []
        return v
