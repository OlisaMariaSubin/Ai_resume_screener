import re

from app.services.docx_parser import extract_text_from_docx
from app.services.pdf_parser import extract_text_from_pdf
from app.services.skill_extractor import extract_skills_from_text
from app.utils.text_cleaning import extract_email, extract_phone

SECTION_HEADERS = {
    "education": ["education", "academic background", "qualifications"],
    "experience": ["experience", "work experience", "employment history", "professional experience"],
    "projects": ["projects", "personal projects", "academic projects"],
    "certifications": ["certifications", "certificates", "licenses"],
    "skills": ["skills", "technical skills", "core competencies"],
}


def _split_sections(text: str) -> dict[str, list[str]]:
    """Split resume text into section -> list of lines, based on heading detection.
    Lines before the first recognized heading go into '_preamble'."""
    lines = text.splitlines()
    sections: dict[str, list[str]] = {"_preamble": []}
    current = "_preamble"

    for line in lines:
        stripped = line.strip().strip(":").lower()
        matched_section = None
        if 0 < len(stripped) <= 40:
            for section, headers in SECTION_HEADERS.items():
                if stripped in headers or any(stripped == h for h in headers):
                    matched_section = section
                    break
        if matched_section:
            current = matched_section
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, [])
        sections[current].append(line)

    return sections


def _extract_name(text: str, email: str) -> str:
    """Best-effort: the first non-empty line that isn't a contact line, header, or
    section title. Returns '' rather than guessing if nothing plausible is found."""
    for line in text.splitlines()[:8]:
        candidate = line.strip()
        if not candidate:
            continue
        if "@" in candidate or any(ch.isdigit() for ch in candidate):
            continue
        lowered = candidate.lower()
        if any(lowered == h for headers in SECTION_HEADERS.values() for h in headers):
            continue
        words = candidate.split()
        if 1 <= len(words) <= 5 and all(re.match(r"^[A-Za-z.'-]+$", w) for w in words):
            return candidate
    return ""


def _list_items(lines: list[str]) -> list[str]:
    items = []
    for line in lines:
        cleaned = re.sub(r"^[\-\*••\|]+\s*", "", line.strip())
        if cleaned:
            items.append(cleaned)
    return items


def parse_resume_bytes(filename: str, content: bytes, extension: str) -> dict:
    """Parse raw resume bytes into the structured shape used throughout the app.

    Returns {"success": False, "error": str} on unrecoverable parse failure, otherwise
    {"success": True, "data": {...}} with never-hallucinated fields (empty when unknown).
    """
    if extension == ".pdf":
        extraction = extract_text_from_pdf(content)
    elif extension == ".docx":
        extraction = extract_text_from_docx(content)
    else:
        return {"success": False, "error": f"Unsupported resume file type '{extension}'"}

    if not extraction["success"]:
        return {"success": False, "error": extraction["error"]}

    raw_text = extraction["text"]
    sections = _split_sections(raw_text)

    email = extract_email(raw_text)
    phone = extract_phone(raw_text)
    name = _extract_name(raw_text, email)

    skills_section_text = "\n".join(sections.get("skills", []))
    skills = extract_skills_from_text(skills_section_text) if skills_section_text else []
    if not skills:
        # Skills weren't confidently sectioned - fall back to scanning the whole document.
        skills = extract_skills_from_text(raw_text)

    education = _list_items(sections.get("education", []))
    experience = _list_items(sections.get("experience", []))
    projects = _list_items(sections.get("projects", []))
    certifications = _list_items(sections.get("certifications", []))

    return {
        "success": True,
        "data": {
            "name": name,
            "email": email,
            "phone": phone,
            "skills": skills,
            "education": education,
            "experience": experience,
            "projects": projects,
            "certifications": certifications,
            "raw_text": raw_text,
        },
    }
