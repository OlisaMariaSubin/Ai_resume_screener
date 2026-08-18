"""Requirement trend panel (Section 9.4) - frequency counts of detected skills
across the screened applicant pool. Purely descriptive aggregation."""


def compute_skill_trends(results: list[dict]) -> list[dict]:
    """results: list of screening result dicts (Section 5 shape).
    Returns skills sorted by descending frequency across scored candidates."""
    scored = [r for r in results if r.get("status") == "scored" and r.get("skills")]
    total = len(scored)
    if total == 0:
        return []

    # Universe = every JD skill that appeared (matched or missing) for any candidate,
    # so a skill nobody has still shows up at 0% rather than being silently omitted.
    universe: set[str] = set()
    for result in scored:
        universe |= set(result["skills"].get("matched", []))
        universe |= set(result["skills"].get("missing", []))

    counts: dict[str, int] = {skill: 0 for skill in universe}
    for result in scored:
        for skill in result["skills"].get("matched", []):
            counts[skill] = counts.get(skill, 0) + 1

    trends = [
        {"skill": skill, "candidates_with_skill": count, "pct_of_pool": round(100 * count / total, 1)}
        for skill, count in counts.items()
    ]
    trends.sort(key=lambda t: -t["candidates_with_skill"])
    return trends
