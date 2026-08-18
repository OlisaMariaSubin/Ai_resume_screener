import re
import unicodedata


def normalize_text(text: str) -> str:
    """Normalize whitespace, unicode quirks, and repeated newlines in extracted text."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    # Common PDF ligature / bullet artifacts
    text = text.replace("•", "- ").replace("", "- ")
    text = text.replace("\xa0", " ")
    # Collapse runs of whitespace on each line, then collapse blank-line runs
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines]
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s.-]?)?(\(?\d{3,4}\)?[\s.-]?)\d{3,4}[\s.-]?\d{3,4}")


def extract_email(text: str) -> str:
    match = EMAIL_RE.search(text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    for line in text.splitlines():
        match = PHONE_RE.search(line)
        if match:
            digits = re.sub(r"\D", "", match.group(0))
            if 7 <= len(digits) <= 15:
                return match.group(0).strip()
    return ""
