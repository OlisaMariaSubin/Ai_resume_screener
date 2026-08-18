import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.database import get_db
from app.models.job import Job
from app.schemas.job import JobResponse
from app.services import scoring
from app.services.jd_parser import parse_jd_file, parse_jd_text
from app.utils.file_validation import ALLOWED_JD_EXTENSIONS, FileValidationError, sanitize_filename, validate_upload

logger = logging.getLogger(__name__)
router = APIRouter()


def _job_response(job: Job) -> JobResponse:
    return JobResponse(
        job_id=job.id,
        title=job.title,
        must_have_skills=job.must_have_skills,
        nice_to_have_skills=job.nice_to_have_skills,
        experience_requirements=job.experience_requirements,
        education_requirements=job.education_requirements,
        scoring_weights=job.scoring_weights,
    )


@router.post("/api/jobs", response_model=JobResponse, status_code=201)
async def create_job(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    content_type = request.headers.get("content-type", "")
    scoring_weights_payload = None

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
        if not description_text:
            raise HTTPException(status_code=422, detail="description must not be blank")
        parsed = parse_jd_text(description_text)

    if not parsed["success"]:
        raise HTTPException(status_code=422, detail=parsed["error"])

    data = parsed["data"]

    weights = None
    if scoring_weights_payload is not None:
        valid, error = scoring.validate_weights(scoring_weights_payload)
        if not valid:
            raise HTTPException(status_code=422, detail=error)
        weights = {
            "skill_match": float(scoring_weights_payload["skill_match"]),
            "text_similarity": float(scoring_weights_payload["text_similarity"]),
            "experience": float(scoring_weights_payload["experience"]),
            "education": float(scoring_weights_payload["education"]),
        }

    job = Job(
        title=title or data["title"],
        description=data["description"],
        must_have_skills=data["must_have_skills"],
        nice_to_have_skills=data["nice_to_have_skills"],
        experience_requirements=data["experience_requirements"],
        education_requirements=data["education_requirements"],
        scoring_weights=weights,
    )
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
