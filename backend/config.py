from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM (supports single key or comma-separated multi-keys)
    gemini_api_key: str = ""
    gemini_api_keys: str = ""
    groq_api_key: str = ""
    groq_api_keys: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # Database
    database_url: str = "postgresql://caduser:cadpass@localhost:5432/caddb"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket: str = "cad-exports"
    minio_secure: bool = False

    # App
    dev_mode: bool = True
    secret_key: str = "dev-secret-key"
    cors_origins: str = "http://localhost:3000"  # Comma-separated list
    max_retries: int = 5
    cad_timeout_seconds: int = 60
    max_alternatives: int = 5

    # Datasets & Knowledge (dynamically rooted to workspace datasets)
    datasets_dir: str = str((Path(__file__).resolve().parent.parent / "datasets").resolve())
    processed_dir: str = str((Path(__file__).resolve().parent.parent / "datasets" / "processed").resolve())
    knowledge_db_path: str = str((Path(__file__).resolve().parent.parent / "datasets" / "processed" / "knowledge.db").resolve())

    model_config = SettingsConfigDict(
        env_file=(".env", str(Path(__file__).resolve().parent / ".env")),
        extra="ignore",
    )

    def get_groq_keys(self) -> List[str]:
        """Returns all configured Groq API keys as a de-duplicated list."""
        combined = f"{self.groq_api_key},{self.groq_api_keys}"
        seen = set()
        keys = []
        for raw in combined.split(","):
            k = raw.strip()
            if k and k not in seen:
                seen.add(k)
                keys.append(k)
        return keys

    def get_gemini_keys(self) -> List[str]:
        """Returns all configured Gemini API keys as a de-duplicated list."""
        combined = f"{self.gemini_api_key},{self.gemini_api_keys}"
        seen = set()
        keys = []
        for raw in combined.split(","):
            k = raw.strip()
            if k and k not in seen:
                seen.add(k)
                keys.append(k)
        return keys

    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if self.dev_mode:
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
