from app.models.job import Job
from app.services import education_normalizer, eligibility_service
from tests.conftest import make_docx_bytes

# ---------------------------------------------------------------------------
# Unit-level: education_normalizer
# ---------------------------------------------------------------------------


def test_normalizer_recognizes_btech_variants():
    for text in ["B.Tech in Computer Science", "Bachelor of Technology", "B Tech CSE"]:
        mentions = education_normalizer.extract_degree_mentions(text)
        assert any(m["name"] == "B.Tech" and m["level"] == "BACHELORS" for m in mentions), text


def test_normalizer_recognizes_be_case_sensitively():
    mentions = education_normalizer.extract_degree_mentions("B.E. Computer Science")
    assert any(m["name"] == "B.E." and m["level"] == "BACHELORS" for m in mentions)

    # Lowercase "be" must never be mistaken for the degree (it's a common English word).
    mentions_lower = education_normalizer.extract_degree_mentions("Looking to be a great engineer someday")
    assert not any(m["name"] == "B.E." for m in mentions_lower)


def test_normalizer_recognizes_mtech():
    mentions = education_normalizer.extract_degree_mentions("M.Tech in Computer Science")
    assert any(m["name"] == "M.Tech" and m["level"] == "MASTERS" for m in mentions)


def test_normalizer_generic_bachelor_degree():
    mentions = education_normalizer.extract_degree_mentions("Bachelor's degree in any discipline")
    assert mentions == [{"name": "Bachelor's Degree", "level": "BACHELORS"}]
    assert education_normalizer.has_only_generic_mentions(mentions) is True


def test_normalizer_branch_extraction():
    assert education_normalizer.extract_branch("B.Tech in Computer Science") == "Computer Science"
    assert education_normalizer.extract_branch("B.Tech Mechanical Engineering") == "Mechanical Engineering"
    assert education_normalizer.extract_branch("B.Tech") == ""


# ---------------------------------------------------------------------------
# Unit-level: eligibility_service.derive_education_eligibility
# ---------------------------------------------------------------------------


def test_derive_eligibility_no_education_mentioned():
    config = eligibility_service.derive_education_eligibility("Python\nSQL\n", "Docker\n", "Backend Engineer\n")
    assert config["requirement_type"] == "none"


def test_derive_eligibility_plain_education_line_is_mandatory():
    # Mirrors the spec's headline example: "Education: B.Tech in Computer Science" with
    # no explicit "required" keyword at all - still a mandatory gate.
    config = eligibility_service.derive_education_eligibility("", "", "Education: B.Tech in Computer Science\n")
    assert config["requirement_type"] == "mandatory"
    assert config["minimum_degree_level"] == "BACHELORS"
    assert config["allowed_degree_names"] == ["B.Tech"]
    assert config["allow_equivalent"] is False


def test_derive_eligibility_both_names_listed_are_both_allowed():
    config = eligibility_service.derive_education_eligibility("B.Tech / B.E. required\n", "", "")
    assert config["requirement_type"] == "mandatory"
    assert set(config["allowed_degree_names"]) == {"B.Tech", "B.E."}


def test_derive_eligibility_or_equivalent_broadens_to_level():
    config = eligibility_service.derive_education_eligibility("B.Tech or equivalent required\n", "", "")
    assert config["allow_equivalent"] is True


def test_jd_parser_keeps_inline_requirement_wording(client):
    """Regression: a line like "Bachelor's degree required" was previously swallowed
    whole by the JD parser's heading heuristic (it contains the bare keyword
    "required"), discarding the degree wording entirely and silently disabling
    eligibility filtering. Only a bare label line ("Required:") should be discarded."""
    response = client.post(
        "/api/jobs",
        json={
            "title": "Data Engineer",
            "description": "Bachelor's degree required\nRequired:\nPython\nSQL\n",
        },
    )
    assert response.status_code == 201
    config = response.json()["eligibility_config"]
    assert config["requirement_type"] == "mandatory"
    assert config["minimum_degree_level"] == "BACHELORS"


def test_derive_eligibility_preferred_section_is_not_mandatory():
    config = eligibility_service.derive_education_eligibility("Python\n", "M.Tech preferred\n", "Backend role\n")
    assert config["requirement_type"] == "preferred"
    assert config["minimum_degree_level"] == "MASTERS"


# ---------------------------------------------------------------------------
# Unit-level: eligibility_service.evaluate_eligibility (the 4 spec test cases)
# ---------------------------------------------------------------------------


def _job_with_config(config: dict) -> Job:
    job = Job()
    job.eligibility_config = config
    return job


def test_eval_test1_btech_required_btech_resume_is_eligible():
    config = eligibility_service.derive_education_eligibility("Education: B.Tech required\n", "", "")
    job = _job_with_config(config)
    result = eligibility_service.evaluate_eligibility({"education": ["B.Tech in Computer Science"]}, job)
    assert result["eligibility_status"] == "ELIGIBLE"


def test_eval_test2_btech_required_mtech_only_is_ineligible():
    config = eligibility_service.derive_education_eligibility("Education: B.Tech required\n", "", "")
    job = _job_with_config(config)
    result = eligibility_service.evaluate_eligibility({"education": ["M.Tech in Computer Science"]}, job)
    assert result["eligibility_status"] == "INELIGIBLE"
    assert "B.Tech" in result["eligibility_reason"]


def test_eval_test3_btech_or_be_allows_be_resume():
    config = eligibility_service.derive_education_eligibility("Education: B.Tech / B.E. required\n", "", "")
    job = _job_with_config(config)
    result = eligibility_service.evaluate_eligibility({"education": ["B.E. Computer Science"]}, job)
    assert result["eligibility_status"] == "ELIGIBLE"


def test_eval_test4_bachelor_required_mtech_no_bachelor_listed():
    """JD requires a (generic) bachelor's degree; resume only lists M.Tech, no
    bachelor's-level entry. Documented policy: a mandatory requirement is only
    satisfied by evidence actually present in the resume - we never assume a Master's
    holder must also hold the underlying Bachelor's, so this is INELIGIBLE (and,
    since M.Tech is above the required level, also flagged overqualified)."""
    config = eligibility_service.derive_education_eligibility("Education: Bachelor's degree required\n", "", "")
    job = _job_with_config(config)
    result = eligibility_service.evaluate_eligibility({"education": ["M.Tech in Computer Science"]}, job)
    assert result["eligibility_status"] == "INELIGIBLE"
    assert result["overqualified"] is True


def test_eval_btech_required_no_higher_degree_allowed_by_default():
    # Section 6: overqualification example - fresher B.Tech role, candidate is M.Tech
    # with no B.Tech listed. allow_higher_degree defaults to False.
    config = eligibility_service.derive_education_eligibility("Education: B.Tech required\n", "", "")
    job = _job_with_config(config)
    result = eligibility_service.evaluate_eligibility({"education": ["M.Tech Computer Science"]}, job)
    assert result["eligibility_status"] == "INELIGIBLE"
    assert result["overqualified"] is True
    assert result["overqualification_reason"]


def test_eval_allow_higher_degree_true_accepts_higher_degree():
    config = eligibility_service.derive_education_eligibility("Education: B.Tech required\n", "", "")
    config["allow_higher_degree"] = True
    job = _job_with_config(config)
    result = eligibility_service.evaluate_eligibility({"education": ["M.Tech Computer Science"]}, job)
    assert result["eligibility_status"] == "ELIGIBLE"
    assert result["overqualified"] is True


def test_eval_holding_both_required_and_higher_degree_is_eligible_and_overqualified():
    config = eligibility_service.derive_education_eligibility("Education: B.Tech required\n", "", "")
    job = _job_with_config(config)
    result = eligibility_service.evaluate_eligibility(
        {"education": ["B.Tech Computer Science", "M.Tech Computer Science"]}, job
    )
    assert result["eligibility_status"] == "ELIGIBLE"
    assert result["overqualified"] is True


def test_eval_preferred_requirement_never_gates_eligibility():
    # Section 5, JD D: "M.Tech preferred" must never reject a B.Tech-only candidate.
    config = eligibility_service.derive_education_eligibility("", "M.Tech preferred\n", "Backend role\n")
    job = _job_with_config(config)
    result = eligibility_service.evaluate_eligibility({"education": ["B.Tech Computer Science"]}, job)
    assert result["eligibility_status"] == "ELIGIBLE"


def test_eval_no_education_requirement_always_eligible():
    job = _job_with_config(eligibility_service.NONE_CONFIG)
    result = eligibility_service.evaluate_eligibility({"education": []}, job)
    assert result["eligibility_status"] == "ELIGIBLE"


def test_eval_empty_education_section_is_ineligible_for_mandatory_requirement():
    config = eligibility_service.derive_education_eligibility("Education: B.Tech required\n", "", "")
    job = _job_with_config(config)
    result = eligibility_service.evaluate_eligibility({"education": []}, job)
    assert result["eligibility_status"] == "INELIGIBLE"
    assert "No recognizable degree" in result["eligibility_reason"]


# ---------------------------------------------------------------------------
# API-level: full pipeline (Test 1 & Test 2, end to end, via /api/screen/bulk)
# ---------------------------------------------------------------------------


def test_api_bulk_screen_gates_ineligible_candidates_before_scoring(client):
    job_resp = client.post(
        "/api/jobs",
        json={
            "title": "Backend Engineer",
            "description": "Education: B.Tech\nRequired:\nPython\nSQL\n",
        },
    )
    job_id = job_resp.json()["job_id"]
    assert job_resp.json()["eligibility_config"]["requirement_type"] == "mandatory"

    eligible_docx = make_docx_bytes(
        ["Eligible Candidate"],
        table_rows=[["Education"], ["B.Tech in Computer Science"], ["Skills"], ["Python, SQL"]],
    )
    ineligible_docx = make_docx_bytes(
        ["Ineligible Candidate"],
        table_rows=[["Education"], ["M.Tech in Computer Science"], ["Skills"], ["Python, SQL"]],
    )

    response = client.post(
        "/api/screen/bulk",
        data={"job_id": job_id},
        files=[
            (
                "files",
                (
                    "eligible.docx",
                    eligible_docx,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            ),
            (
                "files",
                (
                    "ineligible.docx",
                    ineligible_docx,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            ),
        ],
    )
    assert response.status_code == 200
    results = response.json()["results"]

    eligible_result = next(r for r in results if r["filename"] == "eligible.docx")
    ineligible_result = next(r for r in results if r["filename"] == "ineligible.docx")

    assert eligible_result["status"] == "scored"
    assert eligible_result["eligibility_status"] == "ELIGIBLE"
    assert eligible_result["score"] is not None

    assert ineligible_result["status"] == "ineligible"
    assert ineligible_result["eligibility_status"] == "INELIGIBLE"
    assert ineligible_result["score"] is None
    assert ineligible_result["skills"] is None
    assert ineligible_result["eligibility_reason"]
