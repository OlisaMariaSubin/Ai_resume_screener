from app.services import fairness_audit, trend_analysis
from tests.conftest import make_docx_bytes


def test_fairness_scan_flags_known_biased_phrase():
    flags = fairness_audit.scan_jd_language("We need a young and energetic developer who is a native English speaker.")
    categories = {f["category"] for f in flags}
    assert "ageist_language" in categories
    assert "exclusionary_requirements" in categories


def test_fairness_scan_no_false_positive_on_clean_jd():
    flags = fairness_audit.scan_jd_language("We need a skilled Python developer with SQL experience.")
    assert flags == []


def test_score_distribution_counts_must_have_exclusions():
    results = [
        {
            "status": "scored",
            "score": {"overall": 90},
            "skills": {"missing_must_have": []},
        },
        {
            "status": "scored",
            "score": {"overall": 40},
            "skills": {"missing_must_have": ["Docker"]},
        },
        {
            "status": "scored",
            "score": {"overall": 70},
            "skills": {"missing_must_have": ["Docker"]},
        },
    ]
    audit = fairness_audit.compute_score_distribution(results)
    assert audit["total_candidates"] == 3
    docker_entry = next(e for e in audit["excluded_by_must_have_skill"] if e["skill"] == "Docker")
    assert docker_entry["candidates_missing"] == 2


def test_trend_analysis_frequency_math():
    results = [
        {"status": "scored", "skills": {"matched": ["Python", "SQL"], "missing": ["Docker"]}},
        {"status": "scored", "skills": {"matched": ["Python"], "missing": ["SQL", "Docker"]}},
        {"status": "scored", "skills": {"matched": [], "missing": ["Python", "SQL", "Docker"]}},
    ]
    trends = trend_analysis.compute_skill_trends(results)
    by_skill = {t["skill"]: t for t in trends}

    assert by_skill["Python"]["candidates_with_skill"] == 2
    assert by_skill["Python"]["pct_of_pool"] == round(100 * 2 / 3, 1)
    assert by_skill["SQL"]["candidates_with_skill"] == 1
    assert by_skill["Docker"]["candidates_with_skill"] == 0


def test_skill_filter_narrows_results(client):
    job_resp = client.post(
        "/api/jobs",
        json={"title": "Engineer", "description": "Required:\nPython\nSQL\nDocker\n"},
    )
    job_id = job_resp.json()["job_id"]

    docx_with_docker = make_docx_bytes(["Has Docker"], table_rows=[["Skills"], ["Python, SQL, Docker"]])
    docx_without_docker = make_docx_bytes(["No Docker"], table_rows=[["Skills"], ["Python, SQL"]])

    for filename, content in [("a.docx", docx_with_docker), ("b.docx", docx_without_docker)]:
        resume_resp = client.post(
            "/api/resumes",
            files={"file": (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        resume_id = resume_resp.json()["resume_id"]
        client.post("/api/screen", json={"job_id": job_id, "resume_id": resume_id})

    unfiltered = client.get(f"/api/screen/{job_id}/results").json()["results"]
    assert len(unfiltered) == 2

    filtered = client.get(f"/api/screen/{job_id}/results?skills=Docker").json()["results"]
    assert len(filtered) == 1
    assert "Docker" in filtered[0]["skills"]["matched"]


def test_custom_scoring_weights_change_score(client):
    description = "Required:\nPython\nSQL\nDocker\nKubernetes\n"

    default_job = client.post("/api/jobs", json={"title": "A", "description": description}).json()
    custom_job = client.post(
        "/api/jobs",
        json={
            "title": "B",
            "description": description,
            "scoring_weights": {"skill_match": 100, "text_similarity": 0, "experience": 0, "education": 0},
        },
    ).json()
    assert custom_job["scoring_weights"] == {
        "skill_match": 100.0,
        "text_similarity": 0.0,
        "experience": 0.0,
        "education": 0.0,
    }

    docx_bytes = make_docx_bytes(["Candidate"], table_rows=[["Skills"], ["Python, SQL"]])

    resume_id = client.post(
        "/api/resumes",
        files={"file": ("c.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()["resume_id"]

    default_result = client.post(
        "/api/screen", json={"job_id": default_job["job_id"], "resume_id": resume_id}
    ).json()
    custom_result = client.post(
        "/api/screen", json={"job_id": custom_job["job_id"], "resume_id": resume_id}
    ).json()

    assert default_result["score"]["overall"] != custom_result["score"]["overall"]
    assert custom_result["score"]["weights_used"]["skill_match"] == 100.0


def test_invalid_scoring_weights_rejected(client):
    response = client.post(
        "/api/jobs",
        json={
            "title": "Bad Weights",
            "description": "Required:\nPython\n",
            "scoring_weights": {"skill_match": 50, "text_similarity": 50, "experience": 50, "education": 50},
        },
    )
    assert response.status_code == 422
    assert "100" in response.json()["detail"]


def test_explain_degrades_cleanly_without_api_key(client):
    job_resp = client.post("/api/jobs", json={"title": "X", "description": "Required:\nPython\n"})
    job_id = job_resp.json()["job_id"]

    docx_bytes = make_docx_bytes(["Candidate"], table_rows=[["Skills"], ["Python"]])
    resume_id = client.post(
        "/api/resumes",
        files={"file": ("d.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()["resume_id"]

    client.post("/api/screen", json={"job_id": job_id, "resume_id": resume_id})

    response = client.post(f"/api/screen/{job_id}/{resume_id}/explain")
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


def test_trends_endpoint(client):
    job_resp = client.post("/api/jobs", json={"title": "Trends Job", "description": "Required:\nPython\nSQL\n"})
    job_id = job_resp.json()["job_id"]

    docx_bytes = make_docx_bytes(["Candidate"], table_rows=[["Skills"], ["Python"]])
    resume_id = client.post(
        "/api/resumes",
        files={"file": ("e.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()["resume_id"]
    client.post("/api/screen", json={"job_id": job_id, "resume_id": resume_id})

    response = client.get(f"/api/screen/{job_id}/trends")
    assert response.status_code == 200
    trends = response.json()["trends"]
    python_trend = next(t for t in trends if t["skill"] == "Python")
    assert python_trend["candidates_with_skill"] == 1


def test_audit_endpoint(client):
    job_resp = client.post(
        "/api/jobs",
        json={"title": "Audit Job", "description": "We need a young and energetic Python developer.\nRequired:\nPython\n"},
    )
    job_id = job_resp.json()["job_id"]
    response = client.get(f"/api/screen/{job_id}/audit")
    assert response.status_code == 200
    body = response.json()
    assert any(f["category"] == "ageist_language" for f in body["jd_language_flags"])
