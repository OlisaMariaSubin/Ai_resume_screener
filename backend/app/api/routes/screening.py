from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.job import Job
from app.models.resume import Resume
from app.models.screening import ScreeningResult
from app.schemas.screening import ScreeningResultSchema, ScreeningResultsResponse, SingleScreenRequest
from app.services import excel_export_service, explanation_service, fairness_audit, screening_service, trend_analysis

router = APIRouter()


@router.post("/screen/{job_id}/rerun", response_model=ScreeningResultsResponse)
def rerun_screening(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing_rows = db.execute(
        select(ScreeningResult).where(ScreeningResult.job_id == job_id)
    ).scalars().all()
    if not existing_rows:
        raise HTTPException(status_code=422, detail="No screened resumes found for this job")

    resume_ids = {row.resume_id for row in existing_rows}
    resumes = db.execute(select(Resume).where(Resume.id.in_(resume_ids))).scalars().all()
    if not resumes:
        raise HTTPException(status_code=422, detail="No stored resumes found to re-run")

    candidates = [
        {
            "id": resume.id,
            "filename": resume.filename,
            "raw_text": resume.raw_text,
            "structured_data": resume.structured_data,
        }
        for resume in resumes
    ]
    # Re-runs re-evaluate eligibility too (not just scoring) - the recruiter may have
    # edited the JD's education requirement or eligibility_config since the last run.
    results = screening_service.run_pipeline(job, candidates)
    for result in results:
        persist_result(db, job_id, result)

    ranked = load_ranked_results(db, job_id)
    return {"job_id": job_id, "results": ranked}


def persist_result(db: Session, job_id: str, result: dict) -> ScreeningResult:
    """Upsert a screening result keyed by (job_id, candidate_id)."""
    existing = db.execute(
        select(ScreeningResult).where(
            ScreeningResult.job_id == job_id, ScreeningResult.resume_id == result["candidate_id"]
        )
    ).scalar_one_or_none()

    row = existing or ScreeningResult(job_id=job_id, resume_id=result["candidate_id"])
    row.candidate_name = result.get("candidate_name", "")
    row.filename = result.get("filename", "")
    row.status = result["status"]
    row.failure_reason = result.get("failure_reason")

    row.eligibility_status = result.get("eligibility_status")
    row.eligibility_reason = result.get("eligibility_reason")
    row.overqualified = bool(result.get("overqualified", False))
    row.overqualification_reason = result.get("overqualification_reason")
    row.extracted_degree = result.get("extracted_degree", "")
    row.extracted_branch = result.get("extracted_branch", "")
    row.required_degree_text = result.get("required_degree_text")

    score = result.get("score")
    if score:
        row.match_score = score["overall"]
        row.tfidf_score = score["tfidf_similarity"]
        row.embedding_score = score["embedding_similarity"]
        row.skill_match_pct = score["skill_match_pct"]
        row.weights_used = score["weights_used"]
    else:
        row.match_score = None
        row.tfidf_score = None
        row.embedding_score = None
        row.skill_match_pct = None
        row.weights_used = {}

    skills = result.get("skills")
    if skills:
        row.matched_skills = skills["matched"]
        row.missing_skills = skills["missing"]
        row.missing_must_have = skills["missing_must_have"]
        row.missing_nice_to_have = skills["missing_nice_to_have"]
    else:
        row.matched_skills = []
        row.missing_skills = []
        row.missing_must_have = []
        row.missing_nice_to_have = []

    row.explanation = None

    if not existing:
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _eligibility_fields(row: ScreeningResult) -> dict:
    return {
        "eligibility_status": row.eligibility_status,
        "eligibility_reason": row.eligibility_reason,
        "overqualified": row.overqualified,
        "overqualification_reason": row.overqualification_reason,
        "extracted_degree": row.extracted_degree,
        "extracted_branch": row.extracted_branch,
        "required_degree_text": row.required_degree_text,
    }


def row_to_result_dict(row: ScreeningResult) -> dict:
    if row.status != "scored":
        return {
            "candidate_id": row.resume_id,
            "candidate_name": row.candidate_name,
            "filename": row.filename,
            "status": row.status,
            "failure_reason": row.failure_reason,
            "score": None,
            "skills": None,
            "ranking": None,
            **_eligibility_fields(row),
        }
    return {
        "candidate_id": row.resume_id,
        "candidate_name": row.candidate_name,
        "filename": row.filename,
        "status": "scored",
        "failure_reason": None,
        "score": {
            "overall": row.match_score,
            "skill_match_pct": row.skill_match_pct,
            "tfidf_similarity": row.tfidf_score,
            "embedding_similarity": row.embedding_score,
            "weights_used": row.weights_used,
        },
        "skills": {
            "matched": row.matched_skills,
            "missing": row.missing_skills,
            "missing_must_have": row.missing_must_have,
            "missing_nice_to_have": row.missing_nice_to_have,
        },
        "ranking": None,
        **_eligibility_fields(row),
    }


def load_ranked_results(db: Session, job_id: str) -> list[dict]:
    rows = db.execute(select(ScreeningResult).where(ScreeningResult.job_id == job_id)).scalars().all()
    results = [row_to_result_dict(row) for row in rows]

    scored = [r for r in results if r["status"] == "scored"]
    ineligible = [r for r in results if r["status"] == "ineligible"]
    failed = [r for r in results if r["status"] == "failed"]
    scored.sort(key=lambda r: r["score"]["overall"], reverse=True)
    for i, r in enumerate(scored, start=1):
        r["ranking"] = i

    return scored + ineligible + failed


def eligibility_summary(results: list[dict]) -> dict:
    """Section 8 - Eligibility summary: Total uploaded / Eligible / Ineligible / Not
    screened / Overqualified, computed over whatever result set the caller passes in
    (a job's full persisted results, or one bulk-upload batch)."""
    total = len(results)
    eligible = sum(1 for r in results if r["status"] == "scored")
    ineligible = sum(1 for r in results if r["status"] == "ineligible")
    overqualified = sum(1 for r in results if r.get("overqualified"))
    return {
        "total_uploaded": total,
        "eligible": eligible,
        "ineligible": ineligible,
        "not_screened": ineligible,
        "overqualified": overqualified,
    }


@router.post("/screen", response_model=ScreeningResultSchema)
def screen_single(payload: SingleScreenRequest, db: Session = Depends(get_db)):
    job = db.get(Job, payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    resume = db.get(Resume, payload.resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    candidate = {
        "id": resume.id,
        "filename": resume.filename,
        "raw_text": resume.raw_text,
        "structured_data": resume.structured_data,
    }
    results = screening_service.run_pipeline(job, [candidate])
    row = persist_result(db, job.id, results[0])

    ranked = load_ranked_results(db, job.id)
    match = next((r for r in ranked if r["candidate_id"] == row.resume_id), None)
    return match


@router.get("/screen/{job_id}/results", response_model=ScreeningResultsResponse)
def get_results(job_id: str, skills: str | None = Query(default=None), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = load_ranked_results(db, job_id)

    if skills:
        required = {s.strip().lower() for s in skills.split(",") if s.strip()}
        if required:
            results = [
                r
                for r in results
                if r["status"] == "scored"
                and required.issubset({s.lower() for s in r["skills"]["matched"]})
            ]

    return {"job_id": job_id, "results": results}


@router.post("/screen/{job_id}/{resume_id}/explain")
def explain_score(job_id: str, resume_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    row = db.execute(
        select(ScreeningResult).where(ScreeningResult.job_id == job_id, ScreeningResult.resume_id == resume_id)
    ).scalar_one_or_none()
    if not row or row.status != "scored":
        raise HTTPException(status_code=404, detail="Screening result not found")

    if row.explanation:
        return {"explanation": row.explanation, "cached": True}

    if not explanation_service.is_configured():
        raise HTTPException(status_code=503, detail=explanation_service.UNAVAILABLE_MESSAGE)

    result = explanation_service.generate_explanation(
        score={
            "overall": row.match_score,
            "skill_match_pct": row.skill_match_pct,
            "tfidf_similarity": row.tfidf_score,
            "embedding_similarity": row.embedding_score,
            "weights_used": row.weights_used,
        },
        skills={
            "matched": row.matched_skills,
            "missing_must_have": row.missing_must_have,
            "missing_nice_to_have": row.missing_nice_to_have,
        },
        must_have_skills=job.must_have_skills or [],
        nice_to_have_skills=job.nice_to_have_skills or [],
    )

    if not result["success"]:
        raise HTTPException(status_code=503, detail=result["error"])

    row.explanation = result["explanation"]
    db.commit()

    return {"explanation": row.explanation, "cached": False}


@router.get("/screen/{job_id}/audit")
def get_audit(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = load_ranked_results(db, job_id)
    return {
        "jd_language_flags": fairness_audit.scan_jd_language(job.description),
        "score_distribution": fairness_audit.compute_score_distribution(results),
    }


@router.get("/screen/{job_id}/trends")
def get_trends(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = load_ranked_results(db, job_id)
    trends = trend_analysis.compute_skill_trends(results, job)
    return {
        "trends": trends,
        "insights": trend_analysis.compute_recruiter_insights(trends),
        "eligibility_summary": eligibility_summary(results),
    }


@router.get("/screen/{job_id}/export/excel")
def export_excel(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = load_ranked_results(db, job_id)
    trends = trend_analysis.compute_skill_trends(results, job)
    insights = trend_analysis.compute_recruiter_insights(trends)

    scored_ids = [r["candidate_id"] for r in results if r["status"] == "scored"]
    resumes = db.execute(select(Resume).where(Resume.id.in_(scored_ids))).scalars().all() if scored_ids else []
    resume_lookup = {resume.id: resume.structured_data for resume in resumes}

    workbook = excel_export_service.build_screening_workbook(job, results, trends, insights, resume_lookup)

    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in (job.title or "screening")).strip("_")
    filename = f"screening_results_{safe_title or 'job'}.xlsx"

    return StreamingResponse(
        workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
