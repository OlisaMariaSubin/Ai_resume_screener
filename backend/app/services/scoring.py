"""Deterministic, unit-testable scoring logic. See README "Scoring Methodology" for the
documented formulas this module implements.
"""
import re

# Missing a must-have skill costs twice as much toward skill_match_pct as missing a
# nice-to-have skill (the "must-have penalty" from spec Section 7).
MUST_HAVE_SKILL_WEIGHT = 2.0
NICE_TO_HAVE_SKILL_WEIGHT = 1.0

REQUIRED_WEIGHT_KEYS = {"skill_match", "text_similarity", "experience", "education"}

DEGREE_LEVELS = [
    (0, ["diploma"]),
    (1, ["bachelor", "b.tech", "b.e.", "bsc", "b.s.", "undergraduate"]),
    (2, ["master", "m.tech", "msc", "m.s.", "postgraduate", "mba"]),
    (3, ["phd", "doctorate", "doctoral"]),
]

YEARS_RE = re.compile(r"(\d+)\+?\s*years?", re.IGNORECASE)


def compute_skill_match(resume_skills: list[str], must_have: list[str], nice_to_have: list[str]) -> dict:
    """Compare resume skills against JD must-have/nice-to-have skills.

    skill_match_pct = 100 * (matched weight) / (total weight), where must-have skills
    are weighted MUST_HAVE_SKILL_WEIGHT and nice-to-have skills NICE_TO_HAVE_SKILL_WEIGHT.
    This is what makes a missing must-have skill hurt more than a missing nice-to-have one.
    """
    resume_set = {s.lower() for s in resume_skills}
    must_map = {s.lower(): s for s in must_have}
    nice_map = {s.lower(): s for s in nice_to_have if s.lower() not in must_map}

    matched_must = [orig for key, orig in must_map.items() if key in resume_set]
    missing_must = [orig for key, orig in must_map.items() if key not in resume_set]
    matched_nice = [orig for key, orig in nice_map.items() if key in resume_set]
    missing_nice = [orig for key, orig in nice_map.items() if key not in resume_set]

    total_weight = len(must_map) * MUST_HAVE_SKILL_WEIGHT + len(nice_map) * NICE_TO_HAVE_SKILL_WEIGHT
    matched_weight = (
        len(matched_must) * MUST_HAVE_SKILL_WEIGHT + len(matched_nice) * NICE_TO_HAVE_SKILL_WEIGHT
    )

    skill_match_pct = round(100.0 * matched_weight / total_weight, 2) if total_weight else 0.0

    return {
        "matched": matched_must + matched_nice,
        "missing": missing_must + missing_nice,
        "missing_must_have": missing_must,
        "missing_nice_to_have": missing_nice,
        "skill_match_pct": skill_match_pct,
    }


def _max_years(strings: list[str]) -> int | None:
    years = [int(m.group(1)) for s in strings for m in YEARS_RE.finditer(s)]
    return max(years) if years else None


def compute_experience_relevance(resume_experience: list[str], jd_experience_requirements: list[str]) -> float | None:
    """Returns 0-100, or None when relevance can't be reliably determined (no JD
    requirement to compare against, or resume has no experience section at all) -
    None signals the caller to redistribute this component's weight rather than
    inventing a number. Common for campus candidates with no experience section."""
    required_years = _max_years(jd_experience_requirements)
    if required_years is None:
        return None
    if not resume_experience:
        return None

    candidate_years = _max_years(resume_experience)
    if candidate_years is None:
        return 50.0  # experience is listed but years aren't stated - partial credit
    if candidate_years >= required_years:
        return 100.0
    return round(100.0 * candidate_years / required_years, 2)


def _degree_level(text: str) -> int | None:
    lowered = text.lower()
    levels = [level for level, terms in DEGREE_LEVELS if any(t in lowered for t in terms)]
    return max(levels) if levels else None


def compute_education_relevance(resume_education: list[str], jd_education_requirements: list[str]) -> float | None:
    """Returns 0-100, or None when there's nothing reliable to compare (JD states no
    education requirement, or resume lists no education at all)."""
    required_level = _degree_level(" ".join(jd_education_requirements))
    if required_level is None:
        return None
    if not resume_education:
        return None

    candidate_level = _degree_level(" ".join(resume_education))
    if candidate_level is None:
        return 25.0  # education section exists but no recognizable degree level - low partial credit
    if candidate_level >= required_level:
        return 100.0
    return round(100.0 * (candidate_level + 1) / (required_level + 1), 2)


def validate_weights(weights: dict) -> tuple[bool, str]:
    if set(weights.keys()) != REQUIRED_WEIGHT_KEYS:
        return False, f"scoring_weights must include exactly these keys: {sorted(REQUIRED_WEIGHT_KEYS)}"
    for key, value in weights.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            return False, f"scoring_weights.{key} must be a non-negative number"
    total = sum(weights.values())
    if abs(total - 100) > 0.01:
        return False, f"scoring_weights must sum to 100 (got {total})"
    return True, ""


def compute_overall_score(
    skill_match_pct: float,
    text_similarity_pct: float,
    experience_relevance: float | None,
    education_relevance: float | None,
    weights: dict,
) -> dict:
    """Combine the four score components into a 0-100 overall score.

    If experience and/or education relevance is None (unreliable to extract), that
    component's configured weight is redistributed proportionally into skill_match and
    text_similarity, on top of whichever weights (default or custom) are active.
    Returns {"overall": float, "weights_used": dict} where weights_used is the actual
    post-redistribution weighting that produced this specific score.
    """
    applied = dict(weights)
    missing = [c for c, v in (("experience", experience_relevance), ("education", education_relevance)) if v is None]

    if missing:
        redistribute_total = sum(applied[c] for c in missing)
        for c in missing:
            applied[c] = 0.0
        base_total = weights["skill_match"] + weights["text_similarity"]
        if base_total > 0:
            applied["skill_match"] += redistribute_total * (weights["skill_match"] / base_total)
            applied["text_similarity"] += redistribute_total * (weights["text_similarity"] / base_total)
        else:
            applied["skill_match"] += redistribute_total / 2
            applied["text_similarity"] += redistribute_total / 2

    overall = (
        applied["skill_match"] / 100 * skill_match_pct
        + applied["text_similarity"] / 100 * text_similarity_pct
        + applied["experience"] / 100 * (experience_relevance or 0.0)
        + applied["education"] / 100 * (education_relevance or 0.0)
    )
    overall = max(0.0, min(100.0, overall))

    return {
        "overall": round(overall, 2),
        "weights_used": {k: round(v, 2) for k, v in applied.items()},
    }
