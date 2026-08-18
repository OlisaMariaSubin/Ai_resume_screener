"""Evaluate the matching engine's Precision@10 against data/evaluation/*.csv.

Each CSV row is resume_id,jd_id,relevance where resume_id/jd_id are filename
stems under data/sample_resumes/ and data/sample_jds/ (relevance 0-3, treated
as relevant when > 0). Reports the real number - never fabricates a passing
score, and prints an explicit "insufficient data" message when there isn't
enough labelled data to mean anything.
"""
import csv
import glob
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.services import jd_parser, resume_parser, screening_service  # noqa: E402

SAMPLE_RESUMES_DIR = ROOT / "data" / "sample_resumes"
SAMPLE_JDS_DIR = ROOT / "data" / "sample_jds"
EVALUATION_DIR = ROOT / "data" / "evaluation"

MIN_LABELLED_PAIRS = 10
TOP_K = 10


class _JobStub:
    """Minimal stand-in for the Job ORM model - just the attributes
    screening_service.screen_candidates reads."""

    def __init__(self, parsed: dict):
        self.description = parsed["raw_text"]
        self.must_have_skills = parsed["must_have_skills"]
        self.nice_to_have_skills = parsed["nice_to_have_skills"]
        self.experience_requirements = parsed["experience_requirements"]
        self.education_requirements = parsed["education_requirements"]
        self.scoring_weights = None


def load_labels() -> list[dict]:
    rows = []
    for csv_path in glob.glob(str(EVALUATION_DIR / "*.csv")):
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(
                    {"resume_id": row["resume_id"], "jd_id": row["jd_id"], "relevance": int(row["relevance"])}
                )
    return rows


def load_resume(stem: str) -> dict | None:
    for ext in (".pdf", ".docx"):
        path = SAMPLE_RESUMES_DIR / f"{stem}{ext}"
        if path.exists():
            content = path.read_bytes()
            parsed = resume_parser.parse_resume_bytes(path.name, content, ext)
            return parsed["data"] if parsed["success"] else None
    return None


def load_jd(stem: str) -> dict | None:
    path = SAMPLE_JDS_DIR / f"{stem}.txt"
    if not path.exists():
        return None
    parsed = jd_parser.parse_jd_text(path.read_text(encoding="utf-8"))
    return parsed["data"] if parsed["success"] else None


def main() -> None:
    labels = load_labels()
    if len(labels) < MIN_LABELLED_PAIRS:
        print("Evaluation unavailable: insufficient labelled data")
        return

    resumes_cache: dict[str, dict] = {}
    jds_cache: dict[str, dict] = {}

    relevant_by_jd: dict[str, set[str]] = {}
    all_resume_ids: set[str] = set()
    for row in labels:
        all_resume_ids.add(row["resume_id"])
        if row["relevance"] > 0:
            relevant_by_jd.setdefault(row["jd_id"], set()).add(row["resume_id"])

    jd_ids = {row["jd_id"] for row in labels}

    precisions = []
    for jd_id in sorted(jd_ids):
        if jd_id not in jds_cache:
            jds_cache[jd_id] = load_jd(jd_id)
        jd_data = jds_cache[jd_id]
        if not jd_data:
            continue

        candidates = []
        for resume_id in sorted(all_resume_ids):
            if resume_id not in resumes_cache:
                resumes_cache[resume_id] = load_resume(resume_id)
            resume_data = resumes_cache[resume_id]
            if not resume_data:
                continue
            candidates.append({"id": resume_id, "filename": resume_id, "raw_text": resume_data["raw_text"], "structured_data": resume_data})

        if not candidates:
            continue

        job_stub = _JobStub(jd_data)
        ranked = screening_service.screen_candidates(job_stub, candidates)
        top_k = ranked[:TOP_K]

        relevant_ids = relevant_by_jd.get(jd_id, set())
        hits = sum(1 for r in top_k if r["candidate_id"] in relevant_ids)
        precision = hits / TOP_K
        precisions.append(precision)
        print(f"{jd_id}: Precision@{TOP_K} = {precision:.2f} ({hits}/{TOP_K} relevant, {len(top_k)} candidates scored)")

    if not precisions:
        print("Evaluation unavailable: insufficient labelled data")
        return

    overall = sum(precisions) / len(precisions)
    print(f"\nOverall mean Precision@{TOP_K} across {len(precisions)} job(s): {overall:.3f}")
    print(
        "Note: this is computed on a small synthetic, self-labelled dataset - "
        "treat 0.70 as a target to report against honestly, not proof of production accuracy."
    )


if __name__ == "__main__":
    main()
