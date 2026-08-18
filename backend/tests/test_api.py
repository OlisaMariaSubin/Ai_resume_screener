from tests.conftest import make_docx_bytes


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_job_from_text(client):
    payload = {
        "title": "Backend Engineer",
        "description": (
            "Backend Engineer\n\n"
            "Required:\n"
            "Python\nFastAPI\nSQL\n\n"
            "Nice to have:\n"
            "Docker\n"
        ),
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["job_id"]
    assert "Python" in data["must_have_skills"]
    assert "Docker" in data["nice_to_have_skills"]
    assert data["scoring_weights"] is None


def test_create_job_rejects_blank_description(client):
    response = client.post("/api/jobs", json={"title": "X", "description": "   "})
    assert response.status_code == 422


def test_upload_resume(client):
    docx_bytes = make_docx_bytes(
        ["Alex Candidate", "alex@example.com"],
        table_rows=[["Skills"], ["Python, SQL, Docker"]],
    )
    response = client.post(
        "/api/resumes",
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["resume_id"]
    assert "Python" in data["structured_data"]["skills"]


def test_upload_resume_rejects_bad_extension(client):
    response = client.post("/api/resumes", files={"file": ("resume.exe", b"data", "application/octet-stream")})
    assert response.status_code == 422


def test_single_screen_flow(client):
    job_resp = client.post(
        "/api/jobs",
        json={"title": "Data Engineer", "description": "Required:\nPython\nSQL\nDocker\n"},
    )
    job_id = job_resp.json()["job_id"]

    docx_bytes = make_docx_bytes(["Sam Candidate"], table_rows=[["Skills"], ["Python, SQL"]])
    resume_resp = client.post(
        "/api/resumes",
        files={"file": ("sam.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    resume_id = resume_resp.json()["resume_id"]

    screen_resp = client.post("/api/screen", json={"job_id": job_id, "resume_id": resume_id})
    assert screen_resp.status_code == 200
    result = screen_resp.json()
    assert result["status"] == "scored"
    assert 0 <= result["score"]["overall"] <= 100
    assert "Python" in result["skills"]["matched"]
    assert "Docker" in result["skills"]["missing"]

    results_resp = client.get(f"/api/screen/{job_id}/results")
    assert results_resp.status_code == 200
    assert len(results_resp.json()["results"]) == 1
    assert results_resp.json()["results"][0]["ranking"] == 1


def test_screen_rejects_unknown_job(client):
    response = client.post("/api/screen", json={"job_id": "does-not-exist", "resume_id": "also-missing"})
    assert response.status_code == 404


def test_bulk_screen_mixed_batch(client):
    job_resp = client.post(
        "/api/jobs",
        json={"title": "Fullstack Engineer", "description": "Required:\nPython\nReact\n"},
    )
    job_id = job_resp.json()["job_id"]

    good_docx = make_docx_bytes(["Good Candidate"], table_rows=[["Skills"], ["Python, React"]])

    response = client.post(
        "/api/screen/bulk",
        data={"job_id": job_id},
        files=[
            ("files", ("good.docx", good_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("files", ("bad.txt", b"not allowed", "text/plain")),
        ],
    )
    assert response.status_code == 200
    results = response.json()["results"]
    statuses = {r["status"] for r in results}
    assert "scored" in statuses
    assert "failed" in statuses

    scored = [r for r in results if r["status"] == "scored"]
    assert scored[0]["ranking"] == 1
