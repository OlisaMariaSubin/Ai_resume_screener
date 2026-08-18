import uuid

from app.services.resume_parser import parse_resume_bytes
from app.services.screening_service import screen_candidates


def process_bulk_upload(job, files: list[dict]) -> dict:
    """files: list of {"filename": str, "content": bytes, "extension": str}.

    Parses every resume; a single bad file (e.g. scanned PDF with no text) is marked
    failed and excluded from scoring/ranking, but never aborts the rest of the batch.
    Returns {"results": [...], "parsed_resumes": [...]} where parsed_resumes carries the
    structured data the caller needs to persist Resume rows.
    """
    candidates = []
    failed_results = []
    parsed_resumes = []

    for file in files:
        parsed = parse_resume_bytes(file["filename"], file["content"], file["extension"])
        resume_id = str(uuid.uuid4())

        if not parsed["success"]:
            failed_results.append(
                {
                    "candidate_id": resume_id,
                    "candidate_name": "",
                    "filename": file["filename"],
                    "status": "failed",
                    "failure_reason": parsed["error"],
                    "score": None,
                    "skills": None,
                    "ranking": None,
                }
            )
            continue

        data = parsed["data"]
        candidates.append(
            {
                "id": resume_id,
                "filename": file["filename"],
                "raw_text": data["raw_text"],
                "structured_data": data,
            }
        )
        parsed_resumes.append({"id": resume_id, "filename": file["filename"], "data": data})

    scored_results = screen_candidates(job, candidates) if candidates else []

    return {"results": scored_results + failed_results, "parsed_resumes": parsed_resumes}
