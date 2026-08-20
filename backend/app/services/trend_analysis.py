"""Requirement trend panel (Section 9.4) - frequency counts of detected skills across
the screened applicant pool, plus rarity/commonality classification and JD-gap
insights (recruiter-facing enhancement).

Trend stats are computed over status=="scored" results only, i.e. the *eligible*
candidate pool - candidates filtered out during eligibility pre-screening never
distort these percentages (see eligibility_service / screening_service.run_pipeline).
"""

# percentage = candidates_with_skill / total_eligible_candidates * 100
RARITY_THRESHOLDS = [
    ("Very Common", 70.0),
    ("Common", 40.0),
    ("Moderate", 20.0),
    ("Rare", 5.0),
    ("Very Rare", 0.0),
]


def classify_rarity(pct_of_pool: float) -> str:
    for label, threshold in RARITY_THRESHOLDS:
        if pct_of_pool >= threshold:
            return label
    return "Very Rare"


def compute_skill_trends(results: list[dict], job=None) -> list[dict]:
    """results: list of screening result dicts (Section 5 shape).
    Returns skills sorted by descending frequency across the eligible/scored pool.
    job (optional): when given, each entry is flagged with whether that skill is a JD
    must-have/nice-to-have so the frontend/Excel export can highlight requirement gaps.
    """
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

    must_have = {s.lower() for s in (job.must_have_skills or [])} if job else set()
    nice_to_have = {s.lower() for s in (job.nice_to_have_skills or [])} if job else set()

    trends = []
    for skill, count in counts.items():
        pct = round(100 * count / total, 1)
        trends.append(
            {
                "skill": skill,
                "candidates_with_skill": count,
                "pct_of_pool": pct,
                "rarity_category": classify_rarity(pct),
                "is_jd_must_have": skill.lower() in must_have,
                "is_jd_nice_to_have": skill.lower() in nice_to_have,
            }
        )

    trends.sort(key=lambda t: -t["candidates_with_skill"])
    return trends


def compute_requirement_gaps(trends: list[dict]) -> list[dict]:
    """JD must-have skills that are Rare/Very Rare among the eligible applicant pool -
    a signal the requirement may be unnecessarily restrictive, presented as an
    observation for the recruiter to weigh, never an automatic recommendation."""
    gaps = []
    for t in trends:
        if t["is_jd_must_have"] and t["rarity_category"] in ("Rare", "Very Rare"):
            gaps.append(
                {
                    "skill": t["skill"],
                    "pct_of_pool": t["pct_of_pool"],
                    "rarity_category": t["rarity_category"],
                    "insight": (
                        f"JD Requirement Gap: {t['skill']} is {t['rarity_category'].lower()} among "
                        f"applicants ({t['pct_of_pool']}% have it). This is a must-have requirement - "
                        f"worth reviewing whether it's unnecessarily restrictive, or could move to "
                        f"preferred."
                    ),
                }
            )
    return gaps


def compute_recruiter_insights(trends: list[dict]) -> dict:
    """Summarize the trend table into the recruiter-facing questions from the spec:
    what's oversupplied, what's rare, and where the JD may be asking for something the
    applicant pool mostly doesn't have."""
    oversupplied = [t["skill"] for t in trends if t["rarity_category"] == "Very Common"]
    rare_skills = [
        {"skill": t["skill"], "pct_of_pool": t["pct_of_pool"], "rarity_category": t["rarity_category"]}
        for t in trends
        if t["rarity_category"] in ("Rare", "Very Rare")
    ]
    return {
        "oversupplied_skills": oversupplied,
        "rare_skills": rare_skills,
        "jd_requirement_gaps": compute_requirement_gaps(trends),
    }
