import re

from app.services import eligibility_service
from app.services.docx_parser import extract_text_from_docx
from app.services.pdf_parser import extract_text_from_pdf
from app.services.skill_extractor import extract_skills_from_text
from app.utils.text_cleaning import normalize_text

MUST_HAVE_HEADERS = ["required", "must have", "must-have", "mandatory", "qualifications", "requirements"]
NICE_TO_HAVE_HEADERS = ["preferred", "nice to have", "nice-to-have", "bonus", "plus"]

EDUCATION_TERMS = [
    "bachelor", "master", "phd", "b.tech", "b.e.", "m.tech", "bsc", "msc", "degree",
    "diploma", "b.s.", "m.s.",
]

EXPERIENCE_RE = re.compile(r"(\d+\+?\s*(?:-\s*\d+\s*)?\s*years?)", re.IGNORECASE)


def _classify_section(heading: str) -> str | None:
    lowered = heading.strip().strip(":").lower()
    if any(h in lowered for h in MUST_HAVE_HEADERS):
        return "must_have"
    if any(h in lowered for h in NICE_TO_HAVE_HEADERS):
        return "nice_to_have"
    return None


def _looks_like_heading(line: str) -> bool:
    stripped = line.strip().strip(":")
    if not (0 < len(stripped) <= 60):
        return False
    if _classify_section(stripped) is not None:
        return True
    # All-caps heuristic only for multi-word lines, so short skill acronyms
    # (SQL, AWS, CSS, HTML, ...) are never mistaken for section headings.
    return stripped.isupper() and " " in stripped


def _split_jd_sections(text: str) -> dict[str, list[str]]:
    lines = text.splitlines()
    sections: dict[str, list[str]] = {"general": []}
    current = "general"

    for line in lines:
        if _looks_like_heading(line):
            classified = _classify_section(line)
            current = classified or "general"
            sections.setdefault(current, [])
            # A bare label line ("Required:", "Nice to have") carries no content of its
            # own and is discarded. But a line that only *contains* a must/nice-to-have
            # keyword inline ("Bachelor's degree required", "M.Tech preferred") is real
            # content, not just a label - keep it under the section it was classified
            # into, or its text (degree wording, skills, ...) would be silently lost.
            stripped_label = line.strip().strip(":").lower()
            is_bare_label = classified is not None and stripped_label in MUST_HAVE_HEADERS + NICE_TO_HAVE_HEADERS
            if classified is not None and not is_bare_label:
                sections[current].append(line)
            continue
        sections.setdefault(current, [])
        sections[current].append(line)

    return sections


def _extract_title(text: str) -> str:
    for line in text.splitlines()[:5]:
        candidate = line.strip()
        if candidate and len(candidate) <= 100:
            return candidate
    return ""


def parse_jd_text(raw_text: str) -> dict:
    """Parse job description text into structured requirements using deterministic
    heuristics (never an LLM) so requirements are never invented."""
    cleaned = normalize_text(raw_text)
    if not cleaned:
        return {"success": False, "error": "Job description text is empty"}

    sections = _split_jd_sections(cleaned)
    title = _extract_title(cleaned)

    must_have_text = "\n".join(sections.get("must_have", []))
    nice_to_have_text = "\n".join(sections.get("nice_to_have", []))
    general_text = "\n".join(sections.get("general", []))

    must_have_skills = extract_skills_from_text(must_have_text)
    nice_to_have_skills = extract_skills_from_text(nice_to_have_text)

    # Skills mentioned only in the general/unclassified text are uncertain - per spec,
    # when classification is uncertain, keep them in the general skill set rather than
    # guessing must-have vs nice-to-have. We surface them as must-have only if the JD
    # had no explicit section structure at all (whole doc is "general").
    general_skills = extract_skills_from_text(general_text)
    already_classified = {s.lower() for s in must_have_skills + nice_to_have_skills}
    unclassified_extra = [s for s in general_skills if s.lower() not in already_classified]

    if not must_have_skills and not nice_to_have_skills:
        # No explicit sections found at all - treat whole-document skills as must-have,
        # since that's the most common unstructured JD format.
        must_have_skills = unclassified_extra
        unclassified_extra = []

    experience_requirements = sorted(set(EXPERIENCE_RE.findall(cleaned)), key=cleaned.find)

    education_requirements = []
    for line in cleaned.splitlines():
        lowered = line.lower()
        if any(term in lowered for term in EDUCATION_TERMS):
            stripped = line.strip()
            if stripped and stripped not in education_requirements:
                education_requirements.append(stripped)

    education_eligibility = eligibility_service.derive_education_eligibility(
        must_have_text, nice_to_have_text, general_text
    )

    return {
        "success": True,
        "data": {
            "title": title,
            "description": cleaned,
            "must_have_skills": must_have_skills,
            "nice_to_have_skills": nice_to_have_skills,
            "general_skills": unclassified_extra,
            "experience_requirements": experience_requirements,
            "education_requirements": education_requirements,
            "education_eligibility": education_eligibility,
            "raw_text": cleaned,
        },
    }


def parse_jd_file(content: bytes, extension: str) -> dict:
    if extension == ".pdf":
        extraction = extract_text_from_pdf(content)
    elif extension == ".docx":
        extraction = extract_text_from_docx(content)
    elif extension == ".txt":
        try:
            extraction = {"success": True, "text": content.decode("utf-8", errors="replace")}
        except Exception:
            return {"success": False, "error": "Could not read TXT file"}
    else:
        return {"success": False, "error": f"Unsupported job description file type '{extension}'"}

    if not extraction["success"]:
        return {"success": False, "error": extraction["error"]}

    return parse_jd_text(extraction["text"])
