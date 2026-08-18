"""JD fairness-language scan + score-distribution audit (Section 9.3).

This is a fairness-of-process check, not a demographic one - it never infers
or stores anything about a candidate's protected attributes.
"""
from app.utils.skill_dictionary import FAIRNESS_PATTERNS

SCORE_BUCKETS = [
    ("weak (0-59)", 0, 59),
    ("moderate (60-79)", 60, 79),
    ("strong (80-100)", 80, 100),
]


def scan_jd_language(jd_text: str) -> list[dict]:
    """Flag JD wording patterns associated with exclusionary hiring language.
    Deterministic keyword matching against a maintained list - never a guess."""
    lowered = jd_text.lower()
    flags = []
    for category, phrases in FAIRNESS_PATTERNS.items():
        for phrase in phrases:
            if phrase in lowered:
                flags.append({"category": category, "phrase": phrase})
    return flags


def compute_score_distribution(results: list[dict]) -> dict:
    """results: list of screening result dicts (Section 5 shape, status=='scored' only).
    Purely descriptive aggregate stats - never a claim about any protected group."""
    scored = [r for r in results if r.get("status") == "scored" and r.get("score")]
    total = len(scored)

    buckets = {label: 0 for label, _, _ in SCORE_BUCKETS}
    for result in scored:
        overall = result["score"]["overall"]
        for label, low, high in SCORE_BUCKETS:
            if low <= overall <= high:
                buckets[label] += 1
                break

    must_have_exclusion: dict[str, int] = {}
    for result in scored:
        for skill in result.get("skills", {}).get("missing_must_have", []):
            must_have_exclusion[skill] = must_have_exclusion.get(skill, 0) + 1

    return {
        "total_candidates": total,
        "score_distribution": buckets,
        "excluded_by_must_have_skill": [
            {
                "skill": skill,
                "candidates_missing": count,
                "pct_of_pool": round(100 * count / total, 1) if total else 0.0,
            }
            for skill, count in sorted(must_have_exclusion.items(), key=lambda kv: -kv[1])
        ],
    }
