from pydantic import BaseModel


class ResumeStructuredData(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = []
    education: list[str] = []
    experience: list[str] = []
    projects: list[str] = []
    certifications: list[str] = []


class ResumeResponse(BaseModel):
    resume_id: str
    filename: str
    candidate_name: str
    structured_data: ResumeStructuredData


class ResumeContentResponse(BaseModel):
    resume_id: str
    filename: str
    candidate_name: str
    raw_text: str
