from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import bulk, health, jobs, resumes, screening
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.database.init_db import init_db

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Resume Screening Assistant",
    description="Transparent, explainable resume-to-JD matching for campus recruitment.",
    version="1.0.0",
    lifespan=lifespan,
)

# Parse allowed origins as a list, handling comma-separated env values cleanly
if isinstance(settings.allowed_origins, str):
    raw_origins = settings.allowed_origins.split(",")
else:
    raw_origins = settings.allowed_origins

origins = [origin.strip().rstrip("/") for origin in raw_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(screening.router)
app.include_router(bulk.router)