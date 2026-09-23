import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.ai import ParsedResumeOut
from app.services.ai_service import ai_service
from app.utils.file_parser import clean_text, extract_text_from_bytes

SAMPLE_RESUME_TEXT = """
Muhammad Rafay Anwar
Karachi, Pakistan | +92 341 2060044 | muhammadrafayy0@gmail.com
LinkedIn: https://www.linkedin.com/in/muhammad-rafay-anwar-308666296/
GitHub: https://github.com/muhammadrafay

PROFESSIONAL SUMMARY
Artificial Intelligence undergraduate with hands-on project experience in Computer Vision, Python backend development, and workflow automation. Built portfolio projects including a real-time gesture-control system using MediaPipe and OpenCV, a multi-agent automation pipeline using n8n, and a supervised ML model for medical risk prediction. Comfortable across the stack — from data preprocessing and model training to REST API and GraphQL backend development with Django and FastAPI.

TECHNICAL SKILLS
• Programming: Python
• Computer Vision & ML: OpenCV, MediaPipe, scikit-learn, Machine Learning fundamentals, Deep Learning fundamentals, NLP basics
• Backend & APIs: Django, FastAPI, REST APIs, GraphQL, OOP, MVC architecture, authentication & RBAC
• Data & Databases: Pandas, NumPy, MySQL, PostgreSQL, SQLite, database design
• Tools & Workflow: Git, GitHub, VS Code, n8n workflow automation, CrewAI (multi-agent orchestration)

PROJECTS
Real-Time Hand Gesture Screen Controller (Python, MediaPipe, OpenCV, PyAutoGUI)
Built a real-time hand-tracking system that maps gestures to mouse movement, clicks, and scrolling using MediaPipe landmark detection. Optimized the frame-processing pipeline to run smoothly at ~60 FPS on a standard laptop webcam with low CPU usage. Wrote custom coordinate-mapping logic to translate finger positions into precise cursor control.

Multi-Agent News Summarization Pipeline (n8n, CrewAI, Python, LLM APIs)
Designed a multi-agent pipeline (research, summarization, ranking, deduplication, and delivery agents) to collect and condense news by topic. Built the automation workflow in n8n to schedule scraping jobs and route summarized briefs by email. Used an LLM API to generate article summaries and rank relevance across 100+ articles per run.

EDUCATION
BS in Artificial Intelligence | Dawood University of Engineering & Technology
Karachi, Pakistan | 2022 - 2026
CGPA: 3.65

LANGUAGES
• English (Professional Working)
• Urdu (Native)
"""


def test_file_parser_clean_text():
    raw = "Line 1\r\nLine 2\n\n\n\nLine 3\n● Bullet item\n• Another bullet"
    cleaned = clean_text(raw)
    assert "Line 1 Line 2" in cleaned
    assert "• Bullet item" in cleaned
    assert "• Another bullet" in cleaned
    print("[PASS] clean_text unit test passed")


def test_file_parser_txt_bytes():
    raw = b"Sample resume content\nTesting 123"
    extracted = extract_text_from_bytes(raw, "resume.txt")
    assert "Sample resume content" in extracted
    print("[PASS] extract_text_from_bytes unit test passed")


async def test_live_cohere_resume_parsing():
    print("\n--- Starting Live Cohere AI Resume Parsing Test ---")
    parsed: ParsedResumeOut = await ai_service.parse_resume_text(SAMPLE_RESUME_TEXT, resume_id=1)

    print(f"Extracted Name: {parsed.name}")
    assert parsed.name and "Rafay" in parsed.name, f"Expected name to contain 'Rafay', got {parsed.name}"

    print(f"Extracted Email: {parsed.contact.email}")
    assert parsed.contact.email == "muhammadrafayy0@gmail.com"

    print(f"Extracted Phone: {parsed.contact.phone}")
    assert parsed.contact.phone and "2060044" in parsed.contact.phone

    print(f"Extracted Location: {parsed.contact.location}")
    assert parsed.contact.location and "Karachi" in parsed.contact.location

    print(f"Extracted LinkedIn: {parsed.contact.linkedin}")
    assert parsed.contact.linkedin and "linkedin.com" in parsed.contact.linkedin

    # Check Zero Hallucination: No experience was listed in the text!
    print(f"Experience Count: {len(parsed.experience)}")
    assert len(parsed.experience) == 0, f"Expected 0 experience records due to zero-hallucination constraint, got {len(parsed.experience)}"

    # Check Projects
    print(f"Projects Extracted: {len(parsed.projects)}")
    assert len(parsed.projects) >= 2, f"Expected at least 2 projects, got {len(parsed.projects)}"
    for p in parsed.projects:
        print(f"  - Project: {p.name}")
        print(f"    Technologies: {p.technologies}")
        print(f"    Evidence: {p.evidence}")
        assert p.name, "Project name must not be empty"
        assert p.evidence, f"Project '{p.name}' missing evidence quote"

    # Check Education
    print(f"Education Extracted: {len(parsed.education)}")
    assert len(parsed.education) >= 1
    edu = parsed.education[0]
    print(f"  Degree: {edu.degree}")
    print(f"  Institution: {edu.institution}")
    print(f"  CGPA: {edu.cgpa}")
    assert edu.degree and "Artificial Intelligence" in edu.degree
    assert edu.institution and "Dawood" in edu.institution

    # Check Skills Categorization
    print("Skills Breakdown:")
    print(f"  Technical Foundation: {len(parsed.skills.technical_foundation)} skills")
    print(f"  Process & Automation: {len(parsed.skills.process_and_automation)} skills")
    assert len(parsed.skills.technical_foundation) > 0

    # Check ATS Resume Health
    health = parsed.resume_health
    print(f"\nATS Resume Health Score: {health.overall_resume_health_score}/100")
    print(f"  Completeness Score: {health.completeness_score}")
    print(f"  Contact Info Score: {health.contact_information_score}")
    print(f"  Section Structure Score: {health.section_structure_score}")
    print(f"  Skills Clarity Score: {health.skills_clarity_score}")
    print(f"  Project Detail Score: {health.project_detail_score}")
    print(f"  Education Detail Score: {health.education_detail_score}")
    print(f"  Experience Detail Score: {health.experience_detail_score}")
    print(f"  Health Reasons/Observations: {health.reasons}")

    assert 0 <= health.overall_resume_health_score <= 100
    assert health.contact_information_score > 0
    assert health.completeness_score > 0
    print("\n[PASS] Live Cohere AI Resume Parsing & Scoring Test Passed Flawlessly!")


async def main():
    test_file_parser_clean_text()
    test_file_parser_txt_bytes()
    await test_live_cohere_resume_parsing()


if __name__ == "__main__":
    asyncio.run(main())
