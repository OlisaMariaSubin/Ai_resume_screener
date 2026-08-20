# AI Resume Screening Assistant

## Problem

Campus recruiters manually read hundreds of resumes against a single job
description. It's slow, inconsistent between reviewers, and gives no
explanation for why one candidate ranked above another.

## Solution

Upload a job description and one or more resumes. The system parses both,
extracts and normalizes skills, computes a transparent 0–100 match score
(TF-IDF text similarity + explicit skill overlap + experience/education
relevance), shows exactly which required and preferred skills are matched or
missing, and ranks candidates. **The system ranks, informs, and explains its
own reasoning — the recruiter still decides.** No automated hiring decision
is ever made.

## Features

- PDF and DOCX resume parsing (including table content)
- JD parsing from pasted text or an uploaded PDF/DOCX/TXT file, with
  deterministic must-have vs. nice-to-have skill classification
- Skill extraction + alias normalization (`JS` → `JavaScript`,
  `ML` → `Machine Learning`, `K8s` → `Kubernetes`, etc.)
- TF-IDF matching (baseline, always on) with an optional sentence-embedding
  hybrid upgrade
- Transparent, unit-tested 0–100 scoring formula with a documented
  must-have-skill penalty
- Single and bulk screening; one unparsable resume never kills a batch
- Ranked results dashboard: sort, search, minimum-score filter, missing-must-have
  filter, skill multi-select filter
- **Optional add-on modules** (all real, all toggleable):
  - Skill-based filtering on the results table
  - "Explain this score" — on-demand, cached, LLM-generated plain-language
    explanation grounded only in the computed score/skill data
  - JD fairness-language scan + score-distribution audit (never infers or
    stores protected attributes)
  - Requirement-trend panel (skill frequency across the screened pool)
  - Per-job adjustable scoring weights, with the active weights always shown
- Docker Compose for the full stack

**Explicitly out of scope:** candidate chatbot, interview generation, resume
rewriting, personality/facial/sentiment analysis, salary prediction, or any
automated hiring decision.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full pipeline
diagram. Short version: React frontend → FastAPI → parsing layer → skill
extraction/normalization → matching (TF-IDF ± embeddings) → scoring →
SQLAlchemy/SQLite (Postgres-compatible) → results API.

## Tech stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic, SQLAlchemy, SQLite
- **Parsing:** pdfplumber, python-docx, spaCy (tokenization + phrase matching)
- **Matching:** scikit-learn (`TfidfVectorizer`, required baseline),
  sentence-transformers (`all-MiniLM-L6-v2`, optional hybrid upgrade)
- **Optional add-ons:** Google Gemini Python SDK (match explanations, no-ops
  cleanly without an API key)
- **Frontend:** React + Vite, plain CSS
- **Deploy:** Docker + docker-compose; backend targets Render/Railway-style
  hosts, frontend targets Vercel-style static hosts

## Repository structure

```
ai-resume-screening-assistant/
├── backend/            FastAPI app, services, models, tests
├── frontend/            React + Vite app
├── data/                 sample JDs, sample resumes, evaluation set
├── scripts/              seed_database.py, evaluate_precision.py, generate_sample_data.py
├── docs/architecture.md
└── docker-compose.yml
```

## Install & run locally

### Backend

```bash
cd backend
python -m venv venv
./venv/Scripts/activate        # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
cp .env.example .env            # edit as needed (ANTHROPIC_API_KEY optional)
uvicorn app.main:app --reload --port 8000
```

Swagger docs: http://localhost:8000/docs

Optional: seed the database with sample data so the UI has something to show:

```bash
python ../scripts/generate_sample_data.py
python ../scripts/seed_database.py
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env            # VITE_API_BASE_URL, defaults to http://localhost:8000
npm run dev
```

Open http://localhost:5173

### Tests

```bash
cd backend
pytest
```

## Docker

```bash
docker compose up --build
```

Backend: http://localhost:8000 · Frontend: http://localhost:5173

`ANTHROPIC_API_KEY` can be set in your shell before `docker compose up` to
enable the optional "Explain this score" feature; the app runs fine without
it (the explain endpoint just reports "explanations unavailable").

## API

Auto-generated Swagger UI at `/docs`. Key endpoints:

```
GET  /health
POST /api/jobs
POST /api/resumes
POST /api/screen
POST /api/screen/bulk
GET  /api/screen/{job_id}/results?skills=Python,SQL
POST /api/screen/{job_id}/{resume_id}/explain
GET  /api/screen/{job_id}/audit
GET  /api/screen/{job_id}/trends
```

## Matching methodology

1. **TF-IDF baseline (always on).** `TfidfVectorizer` is fit across the JD
   text and every resume text in the current batch; cosine similarity gives
   `tfidf_similarity` (0–1).
2. **Skill match.** Resume skills (extracted with spaCy phrase-matching
   against a maintained skill dictionary, then alias-normalized) are compared
   against the JD's must-have and nice-to-have skills.
3. **Embedding upgrade (optional).** When `MATCHING_METHOD=hybrid`,
   `sentence-transformers/all-MiniLM-L6-v2` embeddings are computed once per
   batch and blended with TF-IDF and skill match (weights from
   `TFIDF_WEIGHT` / `EMBEDDING_WEIGHT` / `SKILL_WEIGHT` in `.env`) into the
   text-similarity component of the overall score. When embeddings aren't
   enabled or the model can't load, `embedding_similarity` is `null` — never
   faked.
4. **Experience/education relevance.** Heuristic year and degree-level
   comparison; returns `None` (not zero) when there's genuinely nothing
   reliable to compare — common for campus resumes with no experience
   section — which triggers weight redistribution rather than an invented
   score.

## Scoring formula (system default)

```
overall = 50% skill_match_pct + 30% text_similarity*100
        + 10% experience_relevance + 10% education_relevance
```

- `skill_match_pct = 100 * matched_weight / total_weight`, where each
  **must-have** skill counts double a **nice-to-have** skill in both the
  numerator and denominator — this is the documented "must-have penalty":
  missing a required skill costs twice what missing a preferred skill costs.
- If `experience_relevance` and/or `education_relevance` can't be reliably
  computed, that component's weight is redistributed proportionally into
  `skill_match` and `text_similarity` — on top of whichever weights (default
  or custom) are active for the job.
- Every score's `weights_used` field reflects the **actual, post-redistribution**
  weights that produced that specific number, not just the job's configured
  weights — so a score is always auditable.
- Companies can override the four weights per job (`scoring_weights` on
  `POST /api/jobs`); an invalid payload (doesn't sum to 100) is rejected with
  a `422` naming the actual sum — the API never silently normalizes it.

## Precision@10 evaluation

```bash
python scripts/generate_sample_data.py
python scripts/evaluate_precision.py
```

This runs the real matching engine against `data/evaluation/relevance.csv` —
a small, self-labelled synthetic dataset (relevance derived directly from the
designed skill overlap between each sample resume and JD, not hand-picked).
With ~30-50 pairs the number is inherently noisy; **treat 0.70 as a target to
report against honestly, not a hard pass/fail gate.** Real output from a run
in this repo:

```
<PASTE THE ACTUAL evaluate_precision.py OUTPUT HERE AFTER RUNNING IT>
```

If there's insufficient labelled data, the script prints
`Evaluation unavailable: insufficient labelled data` instead of a number —
it never fabricates a passing score.

## Limitations

- TF-IDF and skill-dictionary matching are lexical/statistical, not semantic
  understanding — a resume that describes a skill in unusual language may be
  under-matched unless the hybrid embedding mode is enabled.
- The skill dictionary is hand-curated and finite; skills outside it are
  never invented, but also never detected.
- Experience/education relevance uses simple heuristics (year counts, degree
  keywords), not resume comprehension.
- The evaluation set is small and synthetic — a real Precision@10 number
  needs a real, larger, independently-labelled dataset.
- The LLM-generated explanation is advisory text, not a verified fact —
  it's explicitly labelled as such in the UI.

## Future work

- Larger, independently-labelled evaluation dataset
- Configurable skill dictionary (admin-editable, not just hardcoded)
- Resume de-duplication across bulk batches
- Postgres deployment guide alongside SQLite dev setup

## Deployment

- **Backend:** any Render/Railway-style host that can run
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT` from `backend/`, with
  `DATABASE_URL` pointed at a managed Postgres instance for production.
- **Frontend:** any Vercel-style static host building `frontend/` with
  `npm run build` and serving `dist/`; set `VITE_API_BASE_URL` to the
  deployed backend URL at build time.
- **Docker:** `docker-compose.yml` runs both services together for local or
  single-host deployment.
