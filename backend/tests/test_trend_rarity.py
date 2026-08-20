from app.models.job import Job
from app.services import trend_analysis


def _scored(matched, missing=None):
    return {"status": "scored", "skills": {"matched": matched, "missing": missing or []}}


def test_classify_rarity_boundaries():
    assert trend_analysis.classify_rarity(70.0) == "Very Common"
    assert trend_analysis.classify_rarity(69.99) == "Common"
    assert trend_analysis.classify_rarity(40.0) == "Common"
    assert trend_analysis.classify_rarity(39.99) == "Moderate"
    assert trend_analysis.classify_rarity(20.0) == "Moderate"
    assert trend_analysis.classify_rarity(19.99) == "Rare"
    assert trend_analysis.classify_rarity(5.0) == "Rare"
    assert trend_analysis.classify_rarity(4.99) == "Very Rare"
    assert trend_analysis.classify_rarity(0.0) == "Very Rare"


def test_percentage_formula_is_exact():
    """Test 7: percentage = candidates_with_skill / total_eligible_candidates * 100."""
    results = [_scored(["Python"]), _scored(["Python"]), _scored([], ["Python"]), _scored([], ["Python"])]
    trends = trend_analysis.compute_skill_trends(results)
    python = next(t for t in trends if t["skill"] == "Python")
    assert python["candidates_with_skill"] == 2
    assert python["pct_of_pool"] == 50.0
    assert python["rarity_category"] == "Common"


def test_ineligible_candidates_excluded_from_trend_math():
    """Test 8: ineligible candidates (never scored) must not distort trend percentages
    for the eligible/scored pool - compute_skill_trends only looks at status=='scored'."""
    results = [
        _scored(["Kubernetes"]),
        {"status": "ineligible", "skills": None, "eligibility_status": "INELIGIBLE"},
        {"status": "ineligible", "skills": None, "eligibility_status": "INELIGIBLE"},
        {"status": "ineligible", "skills": None, "eligibility_status": "INELIGIBLE"},
    ]
    trends = trend_analysis.compute_skill_trends(results)
    kubernetes = next(t for t in trends if t["skill"] == "Kubernetes")
    # Pool of 1 scored candidate, not 4 - ineligible entries are excluded entirely.
    assert kubernetes["pct_of_pool"] == 100.0
    assert kubernetes["candidates_with_skill"] == 1


def test_jd_requirement_gap_flags_rare_must_have_skill():
    job = Job()
    job.must_have_skills = ["Kubernetes"]
    job.nice_to_have_skills = []

    scored = [_scored(["Kubernetes"])] + [_scored([], ["Kubernetes"]) for _ in range(19)]
    trends = trend_analysis.compute_skill_trends(scored, job)
    kubernetes = next(t for t in trends if t["skill"] == "Kubernetes")
    assert kubernetes["pct_of_pool"] == 5.0
    assert kubernetes["rarity_category"] == "Rare"
    assert kubernetes["is_jd_must_have"] is True

    gaps = trend_analysis.compute_requirement_gaps(trends)
    assert any(g["skill"] == "Kubernetes" for g in gaps)
    assert "JD Requirement Gap" in gaps[0]["insight"]


def test_recruiter_insights_separates_oversupplied_and_rare():
    job = Job()
    job.must_have_skills = []
    job.nice_to_have_skills = []
    results = [_scored(["Python", "Kubernetes"])] + [_scored(["Python"]) for _ in range(9)]
    trends = trend_analysis.compute_skill_trends(results, job)
    insights = trend_analysis.compute_recruiter_insights(trends)
    assert "Python" in insights["oversupplied_skills"]
    assert any(r["skill"] == "Kubernetes" for r in insights["rare_skills"])
