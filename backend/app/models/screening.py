import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    resume_id: Mapped[str] = mapped_column(String(36), index=True)
    candidate_name: Mapped[str] = mapped_column(String(255), default="")
    filename: Mapped[str] = mapped_column(String(255), default="")
    # Nullable: null for ineligible/failed candidates, who are never scored (Section 7 -
    # a candidate filtered out by eligibility must never carry a numeric score, real or 0).
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    tfidf_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    embedding_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    skill_match_pct: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    matched_skills: Mapped[list] = mapped_column(JSON, default=list)
    missing_skills: Mapped[list] = mapped_column(JSON, default=list)
    missing_must_have: Mapped[list] = mapped_column(JSON, default=list)
    missing_nice_to_have: Mapped[list] = mapped_column(JSON, default=list)
    weights_used: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="scored")  # scored | failed | ineligible
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    # Eligibility pre-screening (Section 3/7) - populated for every candidate whose
    # resume was successfully parsed, regardless of status; screening (score/skills)
    # only ever runs when eligibility_status == "ELIGIBLE".
    eligibility_status: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    eligibility_reason: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    overqualified: Mapped[bool] = mapped_column(Boolean, default=False)
    overqualification_reason: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    extracted_degree: Mapped[str] = mapped_column(String(100), default="")
    extracted_branch: Mapped[str] = mapped_column(String(100), default="")
    required_degree_text: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
