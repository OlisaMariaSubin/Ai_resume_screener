from app.utils.skill_dictionary import canonical_skill_name


def normalize_skills(raw_skills: list[str]) -> list[str]:
    """Canonicalize a list of raw skill mentions, de-duplicating while preserving
    first-seen order."""
    seen: dict[str, str] = {}
    for raw in raw_skills:
        canonical = canonical_skill_name(raw)
        key = canonical.lower()
        if key not in seen:
            seen[key] = canonical
    return list(seen.values())
