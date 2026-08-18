from app.services import scoring

DEFAULT_WEIGHTS = {"skill_match": 50, "text_similarity": 30, "experience": 10, "education": 10}


def test_skill_match_full_overlap_is_100():
    result = scoring.compute_skill_match(["Python", "SQL"], ["Python", "SQL"], [])
    assert result["skill_match_pct"] == 100.0


def test_missing_must_have_penalizes_more_than_missing_nice_to_have():
    missing_must = scoring.compute_skill_match(["SQL"], ["Python", "SQL"], [])
    missing_nice = scoring.compute_skill_match(["Python"], ["Python"], ["Docker"])
    assert missing_must["skill_match_pct"] < missing_nice["skill_match_pct"]


def test_matched_skills_raise_score():
    few = scoring.compute_skill_match(["Python"], ["Python", "SQL", "Docker"], [])
    many = scoring.compute_skill_match(["Python", "SQL", "Docker"], ["Python", "SQL", "Docker"], [])
    assert many["skill_match_pct"] > few["skill_match_pct"]


def test_no_required_skills_gives_zero_skill_match():
    result = scoring.compute_skill_match(["Python"], [], [])
    assert result["skill_match_pct"] == 0.0


def test_overall_score_always_within_bounds():
    result = scoring.compute_overall_score(100.0, 100.0, 100.0, 100.0, DEFAULT_WEIGHTS)
    assert result["overall"] == 100.0

    result = scoring.compute_overall_score(0.0, 0.0, 0.0, 0.0, DEFAULT_WEIGHTS)
    assert result["overall"] == 0.0


def test_overall_score_matches_weighted_formula():
    result = scoring.compute_overall_score(80.0, 60.0, 50.0, 40.0, DEFAULT_WEIGHTS)
    expected = 0.5 * 80 + 0.3 * 60 + 0.1 * 50 + 0.1 * 40
    assert result["overall"] == round(expected, 2)
    assert result["weights_used"] == DEFAULT_WEIGHTS


def test_missing_experience_redistributes_weight():
    result = scoring.compute_overall_score(80.0, 60.0, None, 40.0, DEFAULT_WEIGHTS)
    assert result["weights_used"]["experience"] == 0.0
    assert result["weights_used"]["skill_match"] > DEFAULT_WEIGHTS["skill_match"]
    assert result["weights_used"]["text_similarity"] > DEFAULT_WEIGHTS["text_similarity"]
    # weights still sum to 100 after redistribution
    assert round(sum(result["weights_used"].values()), 2) == 100.0


def test_missing_both_experience_and_education_redistributes_fully():
    result = scoring.compute_overall_score(80.0, 60.0, None, None, DEFAULT_WEIGHTS)
    assert result["weights_used"]["experience"] == 0.0
    assert result["weights_used"]["education"] == 0.0
    assert round(sum(result["weights_used"].values()), 2) == 100.0


def test_validate_weights_accepts_valid_sum():
    valid, error = scoring.validate_weights(DEFAULT_WEIGHTS)
    assert valid is True
    assert error == ""


def test_validate_weights_rejects_bad_sum():
    valid, error = scoring.validate_weights({"skill_match": 50, "text_similarity": 30, "experience": 10, "education": 5})
    assert valid is False
    assert "100" in error


def test_validate_weights_rejects_negative():
    valid, error = scoring.validate_weights(
        {"skill_match": -10, "text_similarity": 60, "experience": 30, "education": 20}
    )
    assert valid is False


def test_experience_relevance_none_when_jd_has_no_requirement():
    assert scoring.compute_experience_relevance(["3 years at Acme"], []) is None


def test_experience_relevance_none_when_resume_has_no_experience():
    assert scoring.compute_experience_relevance([], ["3+ years"]) is None


def test_experience_relevance_full_credit_when_meets_requirement():
    assert scoring.compute_experience_relevance(["5 years at Acme"], ["3+ years required"]) == 100.0


def test_education_relevance_full_credit_for_matching_degree():
    assert scoring.compute_education_relevance(["Bachelor of Science"], ["Bachelor's degree required"]) == 100.0
