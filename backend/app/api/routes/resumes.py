from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.database import get_db
from app.models.resume import Resume
from app.schemas.resume import ResumeResponse, ResumeStructuredData
from app.services.resume_parser import parse_resume_bytes
from app.utils.file_validation import ALLOWED_EXTENSIONS, FileValidationError, sanitize_filename, validate_upload

router = APIRouter()


@router.post("/api/resumes", response_model=ResumeResponse, status_code=201)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    settings = get_settings()
    content = await file.read()
    filename = sanitize_filename(file.filename or "")

    try:
        ext = validate_upload(filename, content, file.content_type, settings.max_upload_size_bytes, ALLOWED_EXTENSIONS)
    except FileValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.message)

    parsed = parse_resume_bytes(filename, content, ext)
    if not parsed["success"]:
        raise HTTPException(status_code=422, detail=parsed["error"])

    data = parsed["data"]
    resume = Resume(
        filename=filename,
        candidate_name=data["name"],
        raw_text=data["raw_text"],
        structured_data=data,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return ResumeResponse(
        resume_id=resume.id,
        filename=resume.filename,
        candidate_name=resume.candidate_name,
        structured_data=ResumeStructuredData(**data),
    )


@router.get("/api/resumes/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: str, db: Session = Depends(get_db)):
    resume = db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return ResumeResponse(
        resume_id=resume.id,
        filename=resume.filename,
        candidate_name=resume.candidate_name,
        structured_data=ResumeStructuredData(**resume.structured_data),
    )
