"""Education eligibility pre-screening: runs before scoring so candidates who fail a
mandatory degree requirement are never sent through screening_service (spec: an
ineligible candidate gets eligibility_status=INELIGIBLE / score=None, never a
contaminated low score).

Two halves:
  - derive_education_eligibility(): reads a parsed JD (must-have / nice-to-have /
    general text, same section split jd_parser already computes) and produces a
    structured, recruiter-editable eligibility_config for the Job.
  - evaluate_eligibility(): compares one candidate's structured resume data against a
    Job's eligibility_config and returns eligibility/overqualification fields.

Degree comparisons are level-based (DIPLOMA < BACHELORS < MASTERS < PHD) but a
mandatory requirement that names specific degrees (e.g. "B.Tech") only accepts other
degree names at the same level when the JD says "or equivalent" - see
education_normalizer for the "equivalent" and specific-vs-generic distinction.
"""
import re

from app.services import education_normalizer

VALID_REQUIREMENT_TYPES = {"mandatory", "preferred", "none"}

_LEVEL_LABELS = {"DIPLOMA": "Diploma", "BACHELORS": "Bachelor's", "MASTERS": "Master's", "PHD": "PhD"}

_EQUIVALENT_RE = re.compile(r"\bor equivalent\b|\bequivalent (degree|qualification)\b", re.IGNORECASE)
_OR_HIGHER_RE = re.compile(r"\bor (higher|above)\b", re.IGNORECASE)

NONE_CONFIG = {
    "requirement_type": "none",
    "minimum_degree_level": None,
    "allowed_degree_names": [],
    "allow_equivalent": False,
    "allow_higher_degree": False,
    "source_text": "",
}

# Used for candidates whose eligibility was never evaluated (e.g. resume parsing
# failed before eligibility could even run) - distinct from an ELIGIBLE/INELIGIBLE
# verdict, so the frontend/Excel export can tell "not screened due to a hard filter"
# apart from "couldn't be read at all".
NOT_EVALUATED_FIELDS = {
    "eligibility_status": None,
    "eligibility_reason": None,
    "overqualified": False,
    "overqualification_reason": None,
    "extracted_degree": "",
    "extracted_branch": "",
    "required_degree_text": None,
}


def _level_label(level: str | None) -> str:
    return _LEVEL_LABELS.get(level or "", level or "")


def derive_education_eligibility(must_have_text: str, nice_to_have_text: str, general_text: str) -> dict:
    """Deterministically derive an eligibility_config from a parsed JD's sectioned text.

    Policy: a degree mentioned in the must-have section, OR anywhere in unclassified
    ("general") text, is treated as mandatory - most JDs state education requirements
    ("Education: B.Tech in Computer Science") without an explicit "required" keyword,
    so requiring one would silently disable eligibility filtering for the common case.
    A degree mentioned only in the nice-to-have section is "preferred" and never gates
    screening.
    """
    mandatory_source = f"{must_have_text}\n{general_text}"
    preferred_source = nice_to_have_text

    mandatory_mentions = education_normalizer.extract_degree_mentions(mandatory_source)
    preferred_mentions = education_normalizer.extract_degree_mentions(preferred_source)
    mandatory_names = {m["name"] for m in mandatory_mentions}
    preferred_mentions = [m for m in preferred_mentions if m["name"] not in mandatory_names]

    if mandatory_mentions:
        requirement_type = "mandatory"
        active_mentions = mandatory_mentions
        active_source = mandatory_source
    elif preferred_mentions:
        requirement_type = "preferred"
        active_mentions = preferred_mentions
        active_source = preferred_source
    else:
        return dict(NONE_CONFIG)

    top = education_normalizer.highest_mention(active_mentions)
    minimum_level = top["level"]
    allowed_names = sorted({m["name"] for m in active_mentions if m["level"] == minimum_level})

    is_generic = education_normalizer.has_only_generic_mentions(active_mentions)
    allow_equivalent = is_generic or bool(_EQUIVALENT_RE.search(active_source))
    allow_higher_degree = bool(_OR_HIGHER_RE.search(active_source))

    return {
        "requirement_type": requirement_type,
        "minimum_degree_level": minimum_level,
        "allowed_degree_names": allowed_names,
        "allow_equivalent": allow_equivalent,
        "allow_higher_degree": allow_higher_degree,
        "source_text": active_source.strip()[:300],
    }


def validate_eligibility_config(config: dict) -> tuple[bool, str]:
    if not isinstance(config, dict):
        return False, "eligibility_config must be an object"

    requirement_type = config.get("requirement_type")
    if requirement_type not in VALID_REQUIREMENT_TYPES:
        return False, f"eligibility_config.requirement_type must be one of {sorted(VALID_REQUIREMENT_TYPES)}"

    if requirement_type != "none":
        level = config.get("minimum_degree_level")
        if level not in education_normalizer.DEGREE_LEVELS:
            return False, f"eligibility_config.minimum_degree_level must be one of {education_normalizer.DEGREE_LEVELS}"
        allowed = config.get("allowed_degree_names", [])
        if not isinstance(allowed, list) or not all(isinstance(n, str) for n in allowed):
            return False, "eligibility_config.allowed_degree_names must be a list of strings"

    for key in ("allow_equivalent", "allow_higher_degree"):
        if key in config and not isinstance(config[key], bool):
            return False, f"eligibility_config.{key} must be a boolean"

    return True, ""


def normalize_eligibility_config(payload: dict) -> dict:
    """Fill defaults for a recruiter-supplied eligibility_config override. Caller must
    validate_eligibility_config() first."""
    requirement_type = payload["requirement_type"]
    if requirement_type == "none":
        return dict(NONE_CONFIG)
    return {
        "requirement_type": requirement_type,
        "minimum_degree_level": payload["minimum_degree_level"],
        "allowed_degree_names": list(payload.get("allowed_degree_names") or []),
        "allow_equivalent": bool(payload.get("allow_equivalent", False)),
        "allow_higher_degree": bool(payload.get("allow_higher_degree", False)),
        "source_text": payload.get("source_text", ""),
    }


def _empty_result() -> dict:
    return {
        "eligibility_status": "ELIGIBLE",
        "eligibility_reason": None,
        "overqualified": False,
        "overqualification_reason": None,
        "extracted_degree": "",
        "extracted_branch": "",
        "required_degree_text": None,
    }


def evaluate_eligibility(resume_data: dict, job) -> dict:
    """resume_data: a resume's structured_data dict (has an 'education' list of raw
    lines, never invented). job: the Job ORM instance (reads job.eligibility_config).
    Never runs scoring - callers gate screening_service on eligibility_status here.
    """
    config = job.eligibility_config or NONE_CONFIG
    requirement_type = config.get("requirement_type", "none")

    education_text = "\n".join(resume_data.get("education") or [])
    mentions = education_normalizer.extract_degree_mentions(education_text)
    if not mentions and education_text.strip():
        llm_guess = education_normalizer.classify_ambiguous_degree(education_text)
        if llm_guess:
            mentions = [llm_guess]

    candidate_top = education_normalizer.highest_mention(mentions)
    result = _empty_result()
    result["extracted_degree"] = candidate_top["name"] if candidate_top else ""
    result["extracted_branch"] = education_normalizer.extract_branch(education_text)

    if requirement_type == "none":
        return result

    minimum_level = config["minimum_degree_level"]
    allowed_names = set(config.get("allowed_degree_names") or [])
    allow_equivalent = bool(config.get("allow_equivalent", False))
    allow_higher_degree = bool(config.get("allow_higher_degree", False))
    required_label = " / ".join(sorted(allowed_names)) or _level_label(minimum_level)
    result["required_degree_text"] = required_label

    if candidate_top is None:
        if requirement_type == "preferred":
            return result
        result["eligibility_status"] = "INELIGIBLE"
        result["eligibility_reason"] = (
            f"No recognizable degree found in resume; cannot verify the mandatory "
            f"education requirement ({required_label})."
        )
        return result

    matched_mention = next(
        (
            m
            for m in mentions
            if m["name"] in allowed_names or (allow_equivalent and m["level"] == minimum_level)
        ),
        None,
    )

    if matched_mention:
        higher = [m for m in mentions if education_normalizer.compare_levels(m["level"], minimum_level) > 0]
        if higher:
            top_extra = education_normalizer.highest_mention(higher)
            result["overqualified"] = True
            result["overqualification_reason"] = (
                f"Candidate also holds a {_level_label(top_extra['level'])}-level degree "
                f"({top_extra['name']}), above the JD's required level ({_level_label(minimum_level)})."
            )
        return result

    if requirement_type == "preferred":
        if education_normalizer.compare_levels(candidate_top["level"], minimum_level) > 0:
            result["overqualified"] = True
            result["overqualification_reason"] = (
                f"Candidate holds {candidate_top['name']} ({_level_label(candidate_top['level'])}), above "
                f"the JD's preferred level ({_level_label(minimum_level)})."
            )
        return result

    # requirement_type == "mandatory", no match found
    if education_normalizer.compare_levels(candidate_top["level"], minimum_level) > 0:
        result["overqualified"] = True
        result["overqualification_reason"] = (
            f"Candidate's highest listed degree is {candidate_top['name']} "
            f"({_level_label(candidate_top['level'])}), above the JD's required level "
            f"({_level_label(minimum_level)})."
        )
        if allow_higher_degree:
            return result
        result["eligibility_status"] = "INELIGIBLE"
        result["eligibility_reason"] = (
            f"Required degree ({required_label}) not satisfied; candidate's education is at a higher "
            f"level ({candidate_top['name']}) and this job does not accept a higher degree in place of "
            f"the required one."
        )
        return result

    result["eligibility_status"] = "INELIGIBLE"
    result["eligibility_reason"] = (
        f"Required degree ({required_label}) not satisfied; candidate's highest listed degree is "
        f"{candidate_top['name']}."
    )
    return result
