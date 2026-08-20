from pydantic import BaseModel


class JobResponse(BaseModel):
    job_id: str
    title: str
    description: str
    must_have_skills: list[str]
    nice_to_have_skills: list[str]
    experience_requirements: list[str]
    education_requirements: list[str]
    scoring_weights: dict | None
    eligibility_config: dict | None


class JobUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    scoring_weights: dict | None = None
    eligibility_config: dict | None = None


class JobParsePreviewResponse(BaseModel):
    title: str
    description: str
    must_have_skills: list[str]
    nice_to_have_skills: list[str]
    experience_requirements: list[str]
    education_requirements: list[str]
    education_eligibility: dict
