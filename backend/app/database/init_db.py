from app.database.database import Base, engine

# Import models so they're registered on Base.metadata before create_all runs.
from app.models import job, resume, screening  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
