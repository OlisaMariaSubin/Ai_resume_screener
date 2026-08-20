import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.database import get_db
from app.models.job import Job
from app.schemas.job import JobParsePreviewResponse, JobResponse, JobUpdateRequest
from app.services import eligibility_service, scoring
from app.services.jd_parser import parse_jd_file, parse_jd_text
from app.utils.file_validation import ALLOWED_JD_EXTENSIONS, FileValidationError, sanitize_filename, validate_upload

logger = logging.getLogger(__name__)
router = APIRouter()


def _job_response(job: Job) -> JobResponse:
    return JobResponse(
        job_id=job.id,
        title=job.title,
        description=job.description,
        must_have_skills=job.must_have_skills,
        nice_to_have_skills=job.nice_to_have_skills,
        experience_requirements=job.experience_requirements,
        education_requirements=job.education_requirements,
        scoring_weights=job.scoring_weights,
        eligibility_config=job.eligibility_config,
    )


def _preview_response(data: dict) -> JobParsePreviewResponse:
    return JobParsePreviewResponse(
        title=data["title"],
        description=data["description"],
        must_have_skills=data["must_have_skills"],
        nice_to_have_skills=data["nice_to_have_skills"],
        experience_requirements=data["experience_requirements"],
        education_requirements=data["education_requirements"],
        education_eligibility=data["education_eligibility"],
    )


def _normalize_weights(scoring_weights_payload) -> tuple[dict | None, str | None]:
    if scoring_weights_payload is None:
        return None, None
    valid, error = scoring.validate_weights(scoring_weights_payload)
    if not valid:
        return None, error
    return {
        "skill_match": float(scoring_weights_payload["skill_match"]),
        "text_similarity": float(scoring_weights_payload["text_similarity"]),
        "experience": float(scoring_weights_payload["experience"]),
        "education": float(scoring_weights_payload["education"]),
    }, None


def _normalize_eligibility_config(eligibility_config_payload) -> tuple[dict | None, str | None]:
    """Validate a recruiter-supplied eligibility_config override (Section 5/6 - the
    hard filter must be configurable, not just JD-derived)."""
    if eligibility_config_payload is None:
        return None, None
    valid, error = eligibility_service.validate_eligibility_config(eligibility_config_payload)
    if not valid:
        return None, error
    return eligibility_service.normalize_eligibility_config(eligibility_config_payload), None


def _apply_parsed_data(job: Job, data: dict, title_override: str = "") -> None:
    job.title = title_override or data["title"] or job.title
    job.description = data["description"]
    job.must_have_skills = data["must_have_skills"]
    job.nice_to_have_skills = data["nice_to_have_skills"]
    job.experience_requirements = data["experience_requirements"]
    job.education_requirements = data["education_requirements"]
    job.eligibility_config = data["education_eligibility"]


async def _parse_job_from_request(request: Request) -> tuple[dict, str, dict | None, dict | None]:
    settings = get_settings()
    content_type = request.headers.get("content-type", "")
    scoring_weights_payload = None
    eligibility_config_payload = None

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        title = (form.get("title") or "").strip()
        description_text = (form.get("description") or "").strip()
        upload = form.get("file")

        weights_raw = form.get("scoring_weights")
        if weights_raw:
            try:
                scoring_weights_payload = json.loads(weights_raw)
            except json.JSONDecodeError:
                raise HTTPException(status_code=422, detail="scoring_weights must be valid JSON")

        eligibility_raw = form.get("eligibility_config")
        if eligibility_raw:
            try:
                eligibility_config_payload = json.loads(eligibility_raw)
            except json.JSONDecodeError:
                raise HTTPException(status_code=422, detail="eligibility_config must be valid JSON")

        if upload is not None and getattr(upload, "filename", ""):
            filename = sanitize_filename(upload.filename)
            content = await upload.read()
            try:
                ext = validate_upload(
                    filename, content, upload.content_type, settings.max_upload_size_bytes, ALLOWED_JD_EXTENSIONS
                )
            except FileValidationError as exc:
                raise HTTPException(status_code=422, detail=exc.message)
            parsed = parse_jd_file(content, ext)
        elif description_text:
            parsed = parse_jd_text(description_text)
        else:
            raise HTTPException(status_code=422, detail="Provide either a job description file or description text")
    else:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=422, detail="Malformed request body")
        title = (body.get("title") or "").strip()
        description_text = (body.get("description") or "").strip()
        scoring_weights_payload = body.get("scoring_weights")
        eligibility_config_payload = body.get("eligibility_config")
        if not description_text:
            raise HTTPException(status_code=422, detail="description must not be blank")
        parsed = parse_jd_text(description_text)

    if not parsed["success"]:
        raise HTTPException(status_code=422, detail=parsed["error"])

    weights, weights_error = _normalize_weights(scoring_weights_payload)
    if weights_error:
        raise HTTPException(status_code=422, detail=weights_error)

    eligibility_config, eligibility_error = _normalize_eligibility_config(eligibility_config_payload)
    if eligibility_error:
        raise HTTPException(status_code=422, detail=eligibility_error)

    return parsed["data"], title, weights, eligibility_config


@router.post("/api/jobs/parse-preview", response_model=JobParsePreviewResponse)
async def parse_job_preview(request: Request):
    data, _, _, _ = await _parse_job_from_request(request)
    return _preview_response(data)


@router.post("/api/jobs", response_model=JobResponse, status_code=201)
async def create_job(request: Request, db: Session = Depends(get_db)):
    data, title, weights, eligibility_config_override = await _parse_job_from_request(request)

    job = Job(scoring_weights=weights)
    _apply_parsed_data(job, data, title)
    if eligibility_config_override is not None:
        job.eligibility_config = eligibility_config_override
    db.add(job)
    db.commit()
    db.refresh(job)

    return _job_response(job)


@router.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_response(job)


@router.patch("/api/jobs/{job_id}", response_model=JobResponse)
def update_job(job_id: str, payload: JobUpdateRequest, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if payload.description is not None:
        description_text = payload.description.strip()
        if not description_text:
            raise HTTPException(status_code=422, detail="description must not be blank")
        parsed = parse_jd_text(description_text)
        if not parsed["success"]:
            raise HTTPException(status_code=422, detail=parsed["error"])
        _apply_parsed_data(job, parsed["data"], (payload.title or "").strip())

    if payload.title is not None and payload.description is None:
        job.title = payload.title.strip() or job.title

    if payload.scoring_weights is not None:
        weights, weights_error = _normalize_weights(payload.scoring_weights)
        if weights_error:
            raise HTTPException(status_code=422, detail=weights_error)
        job.scoring_weights = weights

    if payload.eligibility_config is not None:
        eligibility_config, eligibility_error = _normalize_eligibility_config(payload.eligibility_config)
        if eligibility_error:
            raise HTTPException(status_code=422, detail=eligibility_error)
        job.eligibility_config = eligibility_config

    db.commit()
    db.refresh(job)
    return _job_response(job)
