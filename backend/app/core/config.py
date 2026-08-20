from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./resume_screening.db"

    matching_method: str = "tfidf"  # tfidf | hybrid

    tfidf_weight: float = 0.4
    embedding_weight: float = 0.4
    skill_weight: float = 0.2

    default_skill_match_weight: int = 50
    default_text_similarity_weight: int = 30
    default_experience_weight: int = 10
    default_education_weight: int = 10

    max_upload_size_mb: int = 10

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    frontend_origin: str = "http://localhost:5173"

    @property
    def allowed_origins(self) -> list[str]:
        # Strip trailing slashes so origin matching doesn't fail preflight checks
        return [
            origin.strip().rstrip("/") 
            for origin in self.frontend_origin.split(",") 
            if origin.strip()
        ]

    @property
    def default_weights(self) -> dict:
        return {
            "skill_match": self.default_skill_match_weight,
            "text_similarity": self.default_text_similarity_weight,
            "experience": self.default_experience_weight,
            "education": self.default_education_weight,
        }

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()