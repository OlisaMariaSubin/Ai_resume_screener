# Architecture

## Pipeline

```
Recruiter
   |
   v
React (Vite) frontend  --------------------------------------------+
   |  HTTP / JSON, multipart file upload                            |
   v                                                                |
FastAPI backend                                                     |
   |                                                                |
   |-- Parsing layer                                                |
   |     services/pdf_parser.py, docx_parser.py                     |
   |     services/resume_parser.py  -> structured resume data       |
   |     services/jd_parser.py      -> structured JD data           |
   |                                                                |
   |-- Skill extraction / normalization                             |
   |     services/skill_extractor.py (spaCy tokenizer + phrase       |
   |       matching against utils/skill_dictionary.py)               |
   |     services/skill_normalizer.py (alias canonicalization)       |
   |                                                                |
   |-- Matching (TF-IDF +/- Embeddings)                             |
   |     services/tfidf_matcher.py    (scikit-learn, required)      |
   |     services/embedding_matcher.py (sentence-transformers,      |
   |       optional, gated by MATCHING_METHOD=hybrid)                |
   |                                                                |
   |-- Scoring                                                      |
   |     services/scoring.py                                       |
   |       - skill_match_pct (must-have weighted 2x nice-to-have)   |
   |       - experience_relevance / education_relevance             |
   |         (None when unreliable -> weight redistributed)         |
   |       - compute_overall_score() -> 0-100, weights_used          |
   |                                                                |
   |-- Orchestration                                                |
   |     services/screening_service.py (single + bulk, pure)        |
   |     services/bulk_processor.py (parses many resumes, isolates  |
   |       per-file failures so one bad file doesn't kill the batch)|
   |                                                                |
   |-- Optional modules (Section 9)                                 |
   |     services/explanation_service.py (Anthropic API, on demand, |
   |       cached per job+resume)                                   |
   |     services/fairness_audit.py (JD language scan +             |
   |       score-distribution stats)                                |
   |     services/trend_analysis.py (skill-frequency across pool)   |
   |                                                                |
   v                                                                |
SQLite / Postgres-compatible DB (SQLAlchemy)                        |
   models/job.py, resume.py, screening.py                           |
   |                                                                |
   v                                                                |
API responses (Section 5 canonical schema) --------------------------+
```

## Bulk flow

```
POST /api/screen/bulk  {job_id, files[]}
   |
   v
For each file:
   validate -> parse -> (success) add to candidate batch
                      -> (failure) record {status: failed, reason}
   |
   v
screening_service.screen_candidates(job, successful_candidates)
   - TF-IDF fit once across JD + all resumes in the batch
   - (hybrid) embeddings computed once across the batch
   - per-candidate skill match, experience/education relevance, overall score
   - sort descending, assign ranking 1..N
   |
   v
Persist all results (scored + failed) as ScreeningResult rows
   |
   v
GET /api/screen/{job_id}/results re-reads ALL persisted results for the job
   (across every /screen and /screen/bulk call), re-ranks by score, and is
   the single source of truth the frontend renders.
```

## Data contract

Every screening result returned by the API — from `/api/screen`,
`/api/screen/bulk`, or `/api/screen/{job_id}/results` — has the exact shape
documented in the main README under "Canonical data schema". The frontend
never receives or renders an alternate shape.
