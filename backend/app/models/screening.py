import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    resume_id: Mapped[str] = mapped_column(String(36), index=True)
    candidate_name: Mapped[str] = mapped_column(String(255), default="")
    filename: Mapped[str] = mapped_column(String(255), default="")
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    tfidf_score: Mapped[float] = mapped_column(Float, default=0.0)
    embedding_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    skill_match_pct: Mapped[float] = mapped_column(Float, default=0.0)
    matched_skills: Mapped[list] = mapped_column(JSON, default=list)
    missing_skills: Mapped[list] = mapped_column(JSON, default=list)
    missing_must_have: Mapped[list] = mapped_column(JSON, default=list)
    missing_nice_to_have: Mapped[list] = mapped_column(JSON, default=list)
    weights_used: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="scored")  # scored | failed
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
