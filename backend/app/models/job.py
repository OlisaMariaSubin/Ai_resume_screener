import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    must_have_skills: Mapped[list] = mapped_column(JSON, default=list)
    nice_to_have_skills: Mapped[list] = mapped_column(JSON, default=list)
    experience_requirements: Mapped[list] = mapped_column(JSON, default=list)
    education_requirements: Mapped[list] = mapped_column(JSON, default=list)
    # Nullable: null means "use the system default" scoring weights (Section 9.5)
    scoring_weights: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    # Nullable: null means "no mandatory education requirement was detected" - see
    # eligibility_service.derive_education_eligibility / NONE_CONFIG. Recruiter-editable
    # via PATCH /api/jobs/{id}, same override pattern as scoring_weights.
    eligibility_config: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
