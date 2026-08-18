"""Seed the running app's database with the sample JDs and resumes under
data/, and screen every resume against every JD, so the UI has ranked results
to explore immediately after `docker compose up` / local dev startup.

Run scripts/generate_sample_data.py first if data/sample_resumes/ is empty.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.api.routes.screening import persist_result  # noqa: E402
from app.database.database import SessionLocal  # noqa: E402
from app.database.init_db import init_db  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.resume import Resume  # noqa: E402
from app.services import jd_parser, resume_parser, screening_service  # noqa: E402

SAMPLE_RESUMES_DIR = ROOT / "data" / "sample_resumes"
SAMPLE_JDS_DIR = ROOT / "data" / "sample_jds"


def main() -> None:
    init_db()
    db = SessionLocal()

    try:
        jd_files = sorted(SAMPLE_JDS_DIR.glob("*.txt"))
        resume_files = sorted(SAMPLE_RESUMES_DIR.glob("*.docx")) + sorted(SAMPLE_RESUMES_DIR.glob("*.pdf"))

        if not jd_files or not resume_files:
            print("No sample data found. Run scripts/generate_sample_data.py first.")
            return

        resumes = []
        for path in resume_files:
            parsed = resume_parser.parse_resume_bytes(path.name, path.read_bytes(), path.suffix.lower())
            if not parsed["success"]:
                print(f"Skipping unparsable resume {path.name}: {parsed['error']}")
                continue
            data = parsed["data"]
            resume = Resume(
                filename=path.name,
                candidate_name=data["name"],
                raw_text=data["raw_text"],
                structured_data=data,
            )
            db.add(resume)
            db.flush()
            resumes.append({"id": resume.id, "filename": resume.filename, "raw_text": resume.raw_text, "structured_data": data})
        db.commit()
        print(f"Seeded {len(resumes)} resumes.")

        for path in jd_files:
            parsed = jd_parser.parse_jd_text(path.read_text(encoding="utf-8"))
            if not parsed["success"]:
                print(f"Skipping unparsable JD {path.name}: {parsed['error']}")
                continue
            data = parsed["data"]
            job = Job(
                title=data["title"] or path.stem,
                description=data["description"],
                must_have_skills=data["must_have_skills"],
                nice_to_have_skills=data["nice_to_have_skills"],
                experience_requirements=data["experience_requirements"],
                education_requirements=data["education_requirements"],
                scoring_weights=None,
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            results = screening_service.screen_candidates(job, resumes)
            for result in results:
                persist_result(db, job.id, result)

            print(f"Seeded job '{job.title}' (id={job.id}) with {len(results)} screened resumes.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
