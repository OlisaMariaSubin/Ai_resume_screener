from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    overall: float
    skill_match_pct: float
    tfidf_similarity: float
    embedding_similarity: float | None = None
    weights_used: dict


class SkillsBreakdown(BaseModel):
    matched: list[str]
    missing: list[str]
    missing_must_have: list[str]
    missing_nice_to_have: list[str]


class ScreeningResultSchema(BaseModel):
    candidate_id: str
    candidate_name: str
    filename: str
    score: ScoreBreakdown | None = None
    skills: SkillsBreakdown | None = None
    ranking: int | None = None
    explanation: str | None = None
    status: str = "scored"
    failure_reason: str | None = None


class ScreeningResultsResponse(BaseModel):
    job_id: str
    results: list[ScreeningResultSchema]


class SingleScreenRequest(BaseModel):
    job_id: str
    resume_id: str
