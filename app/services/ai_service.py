import json
import logging
import re
from typing import Optional

import cohere
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.ai import (
    ContactInfo,
    ParsedEducation,
    ParsedExperience,
    ParsedProject,
    ParsedResumeOut,
    ResumeHealthOut,
    ResumeStructure,
    SkillsOut,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a professional Resume Intelligence and Information Extraction system.

Your job is to analyze the COMPLETE resume provided by the user and convert
only explicitly supported information into the required structured JSON.

You MUST read and understand the entire resume before generating the output.

============================================================
CORE PRINCIPLE: SOURCE-GROUNDED EXTRACTION
============================================================

Every extracted fact MUST be supported by the actual resume text.
Use the resume as the ONLY source of truth.

NEVER use:
- general knowledge
- common industry expectations
- assumptions
- likely meanings
- outside knowledge
- inferred skills
- inferred employment
- inferred responsibilities
- inferred dates
- inferred companies
- inferred qualifications

If a fact cannot be directly supported by the resume, DO NOT include it.

Use:
- null for missing single-value information
- [] for missing list information

============================================================
1. GENERAL FACTUAL RULES
============================================================

1. Extract ONLY information explicitly supported by the resume.
2. NEVER invent, assume, infer, guess, extrapolate, or hallucinate information.
3. Preserve the original factual meaning.
4. Do not rewrite facts into stronger or more impressive claims.
5. Do not improve the candidate's wording.
6. Do not exaggerate expertise, seniority, responsibility, impact, or experience.
7. Do not convert implied information into explicit information.
8. If information is ambiguous and cannot be safely resolved, use null or [].
9. Missing information MUST remain null or [].

============================================================
2. NAME AND CONTACT INFORMATION
============================================================

Extract contact information only when explicitly present.
Allowed contact fields: name, location, phone, email, linkedin, github.
Do not construct, normalize, or guess missing contact information.
Do not infer location from university location.

============================================================
3. PROFESSIONAL SUMMARY
============================================================

Extract the professional summary only from an explicit summary/profile/objective
section when available. If absent, use null.
Do NOT create a new professional summary from scattered resume information.

============================================================
4. SKILLS
============================================================

Extract skills only when the resume explicitly presents them as skills or
explicitly demonstrates them as technologies/tools used.
A skill MUST NOT be inferred merely because of a degree, project title, or job title.

Categorize skills into:
- project_and_product_coordination
- process_and_automation
- technical_foundation
- data_informed_decision_making
- other

============================================================
5. PROJECTS
============================================================

A project must be extracted as a project only when the resume explicitly
identifies it as a project or places it inside a Projects section.
For each project extract only:
- name
- technologies (explicitly associated with that project)
- description (explicitly stated)
- evidence (short verbatim or near-verbatim quote from the resume)

Do not invent project technologies, outcomes, purpose, metrics, links, or dates.
Do not convert work experience into a project.

============================================================
6. WORK EXPERIENCE / INTERNSHIPS (CRITICAL)
============================================================

Only create an experience record when employment or internship is explicitly
identified as work experience (e.g. Work Experience, Employment, or Internship section).
A job title appearing ONLY in resume header, headline, or summary MUST NOT
automatically be treated as work experience. If only a title appears without
sufficient employment context, experience MUST be [].

For each experience record extract:
- job_title
- company
- location
- start_date
- end_date
- responsibilities
- technologies
- evidence (short verbatim quote)

============================================================
7. EDUCATION
============================================================

Extract only explicitly stated education:
- degree
- institution
- location
- start_date
- end_date
- cgpa
- evidence (short verbatim quote)

============================================================
8. CERTIFICATIONS, ACHIEVEMENTS, LANGUAGES
============================================================

- certifications: name, provider, date, evidence
- achievements: title, description, evidence
- languages: language, proficiency, evidence

============================================================
9. EVIDENCE REQUIREMENT
============================================================

For every extracted factual item, provide a short verbatim excerpt from the resume
as evidence when available. If not available, use "". Do not invent evidence.

============================================================
10. RESUME STRUCTURE
============================================================

Canonical section names:
- Contact Information
- Professional Summary
- Skills
- Projects
- Work Experience
- Education
- Certifications
- Achievements
- Awards
- Publications
- Languages

Note: Contact Information is considered present if contact details (phone, email, etc.)
are found anywhere in the header/document, even without an explicit heading.

============================================================
11. OUT OF SCOPE
============================================================

Do NOT:
- match the resume to a job
- compare with any job description
- perform job matching or candidate ranking

Return ONLY one valid JSON object following the required schema.
"""

JSON_STRUCTURE = """{
    "name": null,
    "contact": {
        "location": null,
        "phone": null,
        "email": null,
        "linkedin": null,
        "github": null
    },
    "professional_summary": null,
    "skills": {
        "project_and_product_coordination": [],
        "process_and_automation": [],
        "technical_foundation": [],
        "data_informed_decision_making": [],
        "other": []
    },
    "projects": [
        {
            "name": "",
            "technologies": [],
            "description": "",
            "evidence": ""
        }
    ],
    "experience": [
        {
            "job_title": null,
            "company": null,
            "location": null,
            "start_date": null,
            "end_date": null,
            "responsibilities": [],
            "technologies": [],
            "evidence": ""
        }
    ],
    "education": [
        {
            "degree": null,
            "institution": null,
            "location": null,
            "start_date": null,
            "end_date": null,
            "cgpa": null,
            "evidence": ""
        }
    ],
    "certifications": [
        {
            "name": "",
            "provider": null,
            "date": null,
            "evidence": ""
        }
    ],
    "achievements": [
        {
            "title": "",
            "description": "",
            "evidence": ""
        }
    ],
    "languages": [
        {
            "language": "",
            "proficiency": null,
            "evidence": ""
        }
    ],
    "resume_understanding": {
        "candidate_profile": "",
        "technical_profile": "",
        "project_profile": "",
        "experience_profile": "",
        "education_profile": "",
        "certification_profile": "",
        "language_profile": ""
    },
    "resume_structure": {
        "present_sections": [],
        "missing_sections": [],
        "incomplete_sections": []
    },
    "resume_health": {
        "completeness_score": 0,
        "contact_information_score": 0,
        "section_structure_score": 0,
        "skills_clarity_score": 0,
        "project_detail_score": 0,
        "education_detail_score": 0,
        "experience_detail_score": 0,
        "overall_resume_health_score": 0,
        "reasons": []
    }
}"""


class AIService:
    def __init__(self):
        self._client: Optional[cohere.AsyncClientV2] = None

    def get_client(self) -> cohere.AsyncClientV2:
        if not settings.COHERE_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="COHERE_API_KEY is not configured on the server.",
            )
        if self._client is None:
            self._client = cohere.AsyncClientV2(api_key=settings.COHERE_API_KEY)
        return self._client

    # ========================================================
    # RULE-BASED HEALTH SCORING
    # ========================================================

    @staticmethod
    def calculate_contact_score(contact: ContactInfo) -> int:
        fields = [contact.location, contact.phone, contact.email, contact.linkedin]
        present = sum(1 for v in fields if v and v.strip())
        return round((present / len(fields)) * 100)

    @staticmethod
    def calculate_skills_score(skills: SkillsOut) -> int:
        total = (
            len(skills.project_and_product_coordination)
            + len(skills.process_and_automation)
            + len(skills.technical_foundation)
            + len(skills.data_informed_decision_making)
            + len(skills.other)
        )
        if total == 0:
            return 0
        return min(100, round((total / 8) * 100))

    @staticmethod
    def calculate_project_score(projects: list[ParsedProject]) -> int:
        if not projects:
            return 0
        scores: list[int] = []
        for project in projects:
            score = 0
            if project.name and project.name.strip():
                score += 40
            if project.technologies:
                score += 30
            if project.description:
                score += 30
            scores.append(score)
        return round(sum(scores) / len(scores))

    @staticmethod
    def calculate_education_score(education: list[ParsedEducation]) -> int:
        if not education:
            return 0
        scores: list[int] = []
        for item in education:
            score = 0
            if item.degree:
                score += 25
            if item.institution:
                score += 25
            if item.location:
                score += 10
            if item.start_date:
                score += 10
            if item.end_date:
                score += 10
            if item.cgpa:
                score += 10
            if item.evidence:
                score += 10
            scores.append(score)
        return round(sum(scores) / len(scores))

    @staticmethod
    def calculate_experience_score(experience: list[ParsedExperience]) -> int:
        if not experience:
            return 0
        scores: list[int] = []
        for item in experience:
            score = 0
            if item.job_title:
                score += 20
            if item.company:
                score += 20
            if item.start_date:
                score += 10
            if item.end_date:
                score += 10
            if item.responsibilities:
                score += 25
            if item.technologies:
                score += 10
            if item.evidence:
                score += 5
            scores.append(score)
        return round(sum(scores) / len(scores))

    @staticmethod
    def calculate_structure_score(structure: ResumeStructure) -> int:
        core_sections = {
            "Contact Information",
            "Professional Summary",
            "Skills",
            "Projects",
            "Education",
            "Languages",
        }
        optional_sections = {
            "Work Experience",
            "Certifications",
            "Achievements",
            "Awards",
            "Publications",
        }
        present = set(structure.present_sections)
        core_present = len(present.intersection(core_sections))
        optional_present = len(present.intersection(optional_sections))

        core_score = (core_present / len(core_sections)) * 80
        optional_score = (optional_present / len(optional_sections)) * 20
        return round(core_score + optional_score)

    @staticmethod
    def calculate_completeness_score(data: ParsedResumeOut) -> int:
        checks = [
            bool(data.name),
            bool(data.contact.email),
            bool(data.contact.phone),
            bool(data.contact.location),
            bool(data.professional_summary),
            bool(
                data.skills.project_and_product_coordination
                or data.skills.process_and_automation
                or data.skills.technical_foundation
                or data.skills.data_informed_decision_making
                or data.skills.other
            ),
            bool(data.projects),
            bool(data.education),
            bool(data.languages),
        ]
        present = sum(1 for v in checks if v)
        return round((present / len(checks)) * 100)

    @classmethod
    def apply_health_scores(cls, data: ParsedResumeOut) -> ParsedResumeOut:
        contact_score = cls.calculate_contact_score(data.contact)
        skills_score = cls.calculate_skills_score(data.skills)
        project_score = cls.calculate_project_score(data.projects)
        education_score = cls.calculate_education_score(data.education)
        experience_score = cls.calculate_experience_score(data.experience)
        structure_score = cls.calculate_structure_score(data.resume_structure)
        completeness_score = cls.calculate_completeness_score(data)

        weighted_score = (
            completeness_score * 0.20
            + contact_score * 0.10
            + structure_score * 0.10
            + skills_score * 0.15
            + project_score * 0.20
            + education_score * 0.10
            + experience_score * 0.15
        )
        overall_score = round(weighted_score)

        reasons: list[str] = []
        if not data.professional_summary:
            reasons.append("Professional summary is missing.")
        if not data.experience:
            reasons.append("No work experience or internship was explicitly identified.")
        if not data.certifications:
            reasons.append("No certifications were explicitly identified.")
        if not data.achievements:
            reasons.append("No achievements or awards were explicitly identified.")
        if data.projects:
            reasons.append(f"{len(data.projects)} project(s) were identified.")
        if data.education:
            reasons.append(f"{len(data.education)} education record(s) were identified.")

        data.resume_health = ResumeHealthOut(
            completeness_score=completeness_score,
            contact_information_score=contact_score,
            section_structure_score=structure_score,
            skills_clarity_score=skills_score,
            project_detail_score=project_score,
            education_detail_score=education_score,
            experience_detail_score=experience_score,
            overall_resume_health_score=overall_score,
            reasons=reasons,
        )
        return data

    # ========================================================
    # PARSE RESUME TEXT VIA COHERE
    # ========================================================

    async def parse_resume_text(self, resume_text: str, resume_id: Optional[int] = None) -> ParsedResumeOut:
        if not resume_text or not resume_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resume text is empty or could not be extracted from the document.",
            )

        client = self.get_client()

        user_prompt = f"""Analyze the COMPLETE resume below.

IMPORTANT:
You must read the entire resume before producing the JSON.
Interpret the text carefully, but NEVER use outside knowledge.

============================================================
REQUIRED JSON STRUCTURE
============================================================
{JSON_STRUCTURE}

============================================================
RESUME START
============================================================
{resume_text}
============================================================
RESUME END
============================================================

Return ONLY the valid JSON object.
"""

        try:
            logger.info("Calling Cohere Async Chat API model=%s for non-blocking resume parsing...", settings.COHERE_MODEL)
            response = await client.chat(
                model=settings.COHERE_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                thinking={"type": "enabled"},
                temperature=0.1,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            logger.error("Cohere API call failed: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Cohere AI service error: {str(e)}",
            )

        # Extract text safely from response content
        raw_output = ""
        if response and response.message and response.message.content:
            for item in response.message.content:
                item_text = getattr(item, "text", None)
                if item_text:
                    raw_output += item_text

        raw_output = raw_output.strip()

        # Remove markdown code fences if present
        if raw_output.startswith("```"):
            raw_output = re.sub(r"^```(?:json)?", "", raw_output, flags=re.IGNORECASE)
            raw_output = re.sub(r"```$", "", raw_output)
            raw_output = raw_output.strip()

        # JSON substring extraction fallback
        if not raw_output.startswith("{"):
            start = raw_output.find("{")
            end = raw_output.rfind("}")
            if start != -1 and end != -1:
                raw_output = raw_output[start : end + 1]

        try:
            parsed_dict = json.loads(raw_output)
        except json.JSONDecodeError as err:
            logger.error("Cohere returned invalid JSON: %s\nRaw output: %s", err, raw_output)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI model produced an unparseable response: {str(err)}",
            )

        try:
            parsed_data = ParsedResumeOut.model_validate(parsed_dict)
        except Exception as val_err:
            logger.error("Parsed resume validation failed: %s", val_err)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Parsed resume structure validation failed: {str(val_err)}",
            )

        parsed_data.resume_id = resume_id

        # Calculate and apply deterministic rule-based health scores
        parsed_data = self.apply_health_scores(parsed_data)
        return parsed_data

    async def analyze_resume_health(self, resume_text: str, resume_id: Optional[int] = None) -> ResumeHealthOut:
        """Parse resume and compute health scoring metrics."""
        parsed_data = await self.parse_resume_text(resume_text, resume_id=resume_id)
        return parsed_data.resume_health


ai_service = AIService()
