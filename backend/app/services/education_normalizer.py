"""Deterministic degree-name/level normalization, shared by JD parsing and resume
parsing so eligibility_service can compare "what the JD asks for" against "what the
candidate has" without relying on exact string matches.

Tier 1 (this module, primary): hand-curated regex patterns, same philosophy as
skill_dictionary.py - explainable and never invents a degree that isn't in the text.

Tier 2 (optional): if a mandatory education requirement exists but the candidate's
education text doesn't match any known pattern, eligibility_service may ask
classify_ambiguous_degree() to use the existing Gemini integration (gated by
settings.gemini_api_key, exactly like explanation_service) as a second opinion. It
never fabricates - an unconfigured/failed call returns None and the caller falls back
to "cannot verify".
"""
import logging
import re

logger = logging.getLogger(__name__)

DEGREE_LEVELS = ["DIPLOMA", "BACHELORS", "MASTERS", "PHD"]
_LEVEL_RANK = {level: rank for rank, level in enumerate(DEGREE_LEVELS)}


def level_rank(level: str) -> int:
    return _LEVEL_RANK[level]


def compare_levels(a: str, b: str) -> int:
    """-1 if a < b, 0 if equal, 1 if a > b."""
    return (level_rank(a) > level_rank(b)) - (level_rank(a) < level_rank(b))


# (canonical_name, level, regex, case_sensitive). Order matters: specific/named degrees
# are listed before their generic ("bachelor's degree") catch-all so a JD/resume that
# names a specific degree is matched by name first. Two-letter abbreviations (B.E.,
# M.A., ...) are matched case-sensitively so we don't mistake the English words "be"/
# "me"/"ma" for a degree - mirrors the ambiguous-short-term handling in
# skill_extractor.py.
_DEGREE_PATTERNS: list[tuple[str, str, str, bool]] = [
    ("B.Tech", "BACHELORS", r"\bb\.?\s?tech(?:nology)?\b", False),
    ("B.Tech", "BACHELORS", r"\bbachelor of technology\b", False),
    ("B.E.", "BACHELORS", r"\bB\.?E\.?\b", True),
    ("B.E.", "BACHELORS", r"\bbachelor of engineering\b", False),
    ("B.Sc.", "BACHELORS", r"\bb\.?\s?sc\b", False),
    ("B.Sc.", "BACHELORS", r"\bbachelor of science\b", False),
    ("BBA", "BACHELORS", r"\bbba\b", False),
    ("BBA", "BACHELORS", r"\bbachelor of business administration\b", False),
    ("BCA", "BACHELORS", r"\bbca\b", False),
    ("BCA", "BACHELORS", r"\bbachelor of computer applications\b", False),
    ("B.Com", "BACHELORS", r"\bb\.?\s?com\b", False),
    ("B.Com", "BACHELORS", r"\bbachelor of commerce\b", False),
    ("B.A.", "BACHELORS", r"\bB\.?A\.?\b", True),
    ("B.A.", "BACHELORS", r"\bbachelor of arts\b", False),
    ("Bachelor's Degree", "BACHELORS", r"\bbachelor'?s?\s+degree\b", False),
    ("Bachelor's Degree", "BACHELORS", r"\bundergraduate degree\b", False),
    ("M.Tech", "MASTERS", r"\bm\.?\s?tech(?:nology)?\b", False),
    ("M.Tech", "MASTERS", r"\bmaster of technology\b", False),
    ("M.E.", "MASTERS", r"\bM\.?E\.?\b", True),
    ("M.E.", "MASTERS", r"\bmaster of engineering\b", False),
    ("M.Sc.", "MASTERS", r"\bm\.?\s?sc\b", False),
    ("M.Sc.", "MASTERS", r"\bmaster of science\b", False),
    ("MBA", "MASTERS", r"\bmba\b", False),
    ("MBA", "MASTERS", r"\bmaster of business administration\b", False),
    ("MCA", "MASTERS", r"\bmca\b", False),
    ("MCA", "MASTERS", r"\bmaster of computer applications\b", False),
    ("M.Com", "MASTERS", r"\bm\.?\s?com\b", False),
    ("M.A.", "MASTERS", r"\bM\.?A\.?\b", True),
    ("M.A.", "MASTERS", r"\bmaster of arts\b", False),
    ("Master's Degree", "MASTERS", r"\bmaster'?s?\s+degree\b", False),
    ("Master's Degree", "MASTERS", r"\bpostgraduate degree\b", False),
    ("PhD", "PHD", r"\bph\.?\s?d\.?\b", False),
    ("PhD", "PHD", r"\bdoctorate\b", False),
    ("PhD", "PHD", r"\bdoctoral\b", False),
    ("Diploma", "DIPLOMA", r"\bdiploma\b", False),
]

_COMPILED = [
    (name, level, re.compile(pattern) if case_sensitive else re.compile(pattern, re.IGNORECASE), case_sensitive)
    for name, level, pattern, case_sensitive in _DEGREE_PATTERNS
]

_GENERIC_NAMES = {"Bachelor's Degree", "Master's Degree"}

_BRANCH_PATTERNS: list[tuple[str, str]] = [
    ("Computer Science", r"\b(computer science|cse|c\.s\.e\.?)\b"),
    ("Information Technology", r"\b(information technology|\bit\b)\b"),
    ("Electronics and Communication", r"\b(electronics (and|&) communication|ece)\b"),
    ("Electrical and Electronics", r"\b(electrical (and|&) electronics|eee)\b"),
    ("Electrical Engineering", r"\belectrical engineering\b"),
    ("Mechanical Engineering", r"\b(mechanical engineering|\bmech\b)\b"),
    ("Civil Engineering", r"\bcivil engineering\b"),
    ("Chemical Engineering", r"\bchemical engineering\b"),
    ("Artificial Intelligence", r"\b(artificial intelligence( and machine learning)?|\bai\s?/?\s?ml\b)\b"),
    ("Data Science", r"\bdata science\b"),
    ("Biotechnology", r"\bbiotechnology\b"),
    ("Information Science", r"\binformation science\b"),
]
_COMPILED_BRANCHES = [(name, re.compile(pattern, re.IGNORECASE)) for name, pattern in _BRANCH_PATTERNS]


def extract_degree_mentions(text: str) -> list[dict]:
    """Scan free text for every distinct known degree name it mentions.

    Returns a list of {"name": canonical_name, "level": level} in first-seen order,
    deduplicated by name. Purely deterministic - never invents a degree.
    """
    if not text:
        return []

    found: dict[str, str] = {}
    for name, level, regex, _case_sensitive in _COMPILED:
        if name in found:
            continue
        if regex.search(text):
            found[name] = level

    return [{"name": name, "level": level} for name, level in found.items()]


def has_only_generic_mentions(mentions: list[dict]) -> bool:
    """True if every degree mention found is a generic ('Bachelor's Degree') marker
    rather than a specific named degree - used to decide whether a JD requirement is
    already level-based (generic) versus name-based (specific)."""
    return bool(mentions) and all(m["name"] in _GENERIC_NAMES for m in mentions)


def highest_mention(mentions: list[dict]) -> dict | None:
    if not mentions:
        return None
    return max(mentions, key=lambda m: level_rank(m["level"]))


def extract_branch(text: str) -> str:
    """Best-effort specialization/branch extraction. Returns '' rather than guessing
    when nothing recognizable is found."""
    if not text:
        return ""
    for name, regex in _COMPILED_BRANCHES:
        if regex.search(text):
            return name
    return ""


def classify_ambiguous_degree(text: str) -> dict | None:
    """Tier-2 fallback: ask the existing Gemini integration to classify education text
    that Tier-1 regex couldn't recognize. Gated by settings.gemini_api_key exactly like
    explanation_service - returns None (never a guess) when unconfigured, unreachable,
    or the model itself is unsure.
    """
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.gemini_api_key.strip():
        return None

    try:
        from google import genai
    except ImportError:
        return None

    prompt = (
        "Classify the following education text into exactly one degree level: "
        "DIPLOMA, BACHELORS, MASTERS, PHD, or UNKNOWN if it does not clearly describe "
        "one of those. Respond with only the single word.\n\n"
        f"Education text: {text}"
    )

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(model=settings.gemini_model, contents=prompt)
        level = (response.text or "").strip().upper()
    except Exception as exc:
        logger.warning("Ambiguous degree classification failed: %s", exc)
        return None

    if level not in DEGREE_LEVELS:
        return None

    return {"name": text.strip()[:100] or "Unrecognized degree", "level": level}
