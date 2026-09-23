import io
import os
import re
from pathlib import Path
from typing import Optional

import docx
import httpx
import pypdf

from app.utils.supabase_client import supabase_client


def is_heading(line: str) -> bool:
    line = line.strip()
    if not line:
        return False

    known_headings = {
        "PROFESSIONAL SUMMARY",
        "SUMMARY",
        "PROFILE",
        "RELEVANT SKILLS",
        "SKILLS",
        "TECHNICAL SKILLS",
        "WORK EXPERIENCE",
        "EXPERIENCE",
        "PROFESSIONAL EXPERIENCE",
        "EMPLOYMENT HISTORY",
        "INTERNSHIPS",
        "RELEVANT PROJECTS",
        "TECHNICAL PROJECTS",
        "PROJECTS",
        "EDUCATION",
        "CERTIFICATIONS",
        "CERTIFICATES",
        "LANGUAGES",
        "ACHIEVEMENTS",
        "AWARDS",
        "PUBLICATIONS",
        "INTERESTS",
    }

    if line.upper() in known_headings:
        return True

    # Short all-uppercase lines
    if len(line) <= 50 and line.upper() == line and any(c.isalpha() for c in line):
        return True

    return False


def should_join_lines(previous: str, current: str) -> bool:
    # Never join bullets
    if previous.startswith("•") or current.startswith("•"):
        return False

    # Never join headings
    if is_heading(previous) or is_heading(current):
        return False

    # Hyphenated continuation
    if previous.endswith("-"):
        return True

    # Lowercase continuation
    if current and current[0].islower():
        return True

    # Sentence-ending punctuation
    if previous.endswith((".", "!", "?", ":")):
        return False

    # Resume line wrapping
    if len(previous) < 100:
        return True

    return False


def clean_text(text: str) -> str:
    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize bullet characters
    text = text.replace("●", "•").replace("▪", "•").replace("◦", "•")

    # Normalize spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Fix hyphenated words broken across lines
    text = re.sub(r"(?<!\n)-\n(?=[a-z])", "-", text)

    lines = text.split("\n")
    cleaned_lines: list[str] = []

    for line in lines:
        line = line.strip()

        if not line:
            cleaned_lines.append("")
            continue

        if re.match(r"^--- Page \d+ ---$", line):
            cleaned_lines.append(line)
            continue

        if line.startswith("•"):
            cleaned_lines.append(line)
            continue

        if not cleaned_lines:
            cleaned_lines.append(line)
            continue

        previous = cleaned_lines[-1]

        if not previous:
            cleaned_lines.append(line)
            continue

        if re.match(r"^--- Page \d+ ---$", previous):
            cleaned_lines.append(line)
            continue

        if is_heading(previous) or is_heading(line):
            cleaned_lines.append(line)
            continue

        if should_join_lines(previous, line):
            if previous.endswith("-"):
                cleaned_lines[-1] = previous + line
            else:
                cleaned_lines[-1] = previous + " " + line
        else:
            cleaned_lines.append(line)

    result = "\n".join(cleaned_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def extract_pdf_bytes(content: bytes) -> str:
    """Extract text from PDF file bytes using pypdf."""
    reader = pypdf.PdfReader(io.BytesIO(content))
    pages: list[str] = []

    for idx, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(f"--- Page {idx} ---\n{page_text}")

    return "\n\n".join(pages)


def extract_docx_bytes(content: bytes) -> str:
    """Extract text from DOCX file bytes using python-docx."""
    doc = docx.Document(io.BytesIO(content))
    paragraphs: list[str] = []

    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            paragraphs.append(txt)

    # Also capture table contents
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                paragraphs.append(row_text)

    return "\n".join(paragraphs)


def extract_text_from_bytes(content: bytes, file_name_or_ext: str) -> str:
    """Extract and clean text from raw bytes based on extension."""
    ext = Path(file_name_or_ext).suffix.lower()
    if not ext and not file_name_or_ext.startswith("."):
        ext = f".{file_name_or_ext.lower()}"

    if ext == ".pdf":
        raw_text = extract_pdf_bytes(content)
    elif ext in {".docx", ".doc"}:
        raw_text = extract_docx_bytes(content)
    elif ext in {".txt", ".md"}:
        raw_text = content.decode("utf-8", errors="ignore")
    else:
        # Default try pdf then docx
        try:
            raw_text = extract_pdf_bytes(content)
        except Exception:
            raw_text = content.decode("utf-8", errors="ignore")

    return clean_text(raw_text)


async def fetch_resume_bytes(file_path_or_url: str) -> bytes:
    """Fetch resume file bytes from local disk, Supabase storage bucket, or HTTP public URL."""
    # Check if it's a local file first
    if os.path.isfile(file_path_or_url):
        with open(file_path_or_url, "rb") as f:
            return f.read()

    # If it is an HTTP/HTTPS URL, download via httpx
    if file_path_or_url.startswith("http://") or file_path_or_url.startswith("https://"):
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(file_path_or_url)
            resp.raise_for_status()
            return resp.content

    # Otherwise treat as Supabase Storage relative path
    storage_path = file_path_or_url.lstrip("/")
    if storage_path.startswith("resumes/"):
        storage_path = storage_path.replace("resumes/", "", 1)

    try:
        data = supabase_client.storage.from_("resumes").download(storage_path)
        return data
    except Exception as e:
        raise ValueError(f"Unable to retrieve file from storage or URL: {file_path_or_url}. Error: {e}")
