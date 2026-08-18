import logging
import re

import spacy
from spacy.matcher import PhraseMatcher

from app.services.skill_normalizer import normalize_skills
from app.utils.skill_dictionary import ALL_SKILLS, SKILL_ALIASES

logger = logging.getLogger(__name__)

# A blank English pipeline gives us spaCy's tokenizer (used for phrase boundary
# handling) without requiring a downloaded statistical model.
_nlp = spacy.blank("en")

_ALL_TERMS = sorted(set(ALL_SKILLS) | set(SKILL_ALIASES.keys()), key=len, reverse=True)
_matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
_matcher.add("SKILL", [_nlp.make_doc(term) for term in _ALL_TERMS])

# Terms that are ambiguous as short standalone tokens (e.g. "R", "Go", "C") - require
# them to appear as a clearly delimited token, not part of a stray fragment.
_AMBIGUOUS_SHORT_TERMS = {"r", "go", "c"}


def extract_skills_from_text(text: str) -> list[str]:
    """Detect skill mentions in free text using spaCy tokenization + phrase matching
    against the skill dictionary (never spaCy NER alone, and never invented skills)."""
    if not text:
        return []

    doc = _nlp(text)
    matches = _matcher(doc)

    found: list[str] = []
    for _, start, end in matches:
        span_text = doc[start:end].text
        lowered = span_text.lower().strip()
        if lowered in _AMBIGUOUS_SHORT_TERMS:
            # Require the ambiguous short term to be its own token, not e.g. "Go" inside "Google"
            if not re.fullmatch(r"[A-Za-z][+#.]*", span_text):
                continue
        found.append(span_text)

    return normalize_skills(found)
