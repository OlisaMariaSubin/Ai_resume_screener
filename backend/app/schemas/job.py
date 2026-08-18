from pydantic import BaseModel


class JobResponse(BaseModel):
    job_id: str
    title: str
    must_have_skills: list[str]
    nice_to_have_skills: list[str]
    experience_requirements: list[str]
    education_requirements: list[str]
    scoring_weights: dict | None
