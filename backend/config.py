from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM
    gemini_api_key: str = ""
    groq_api_key: str = ""
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
    cors_origins: str = "http://localhost:3000"
    max_retries: int = 5
    cad_timeout_seconds: int = 60
    max_alternatives: int = 5

    # Datasets & Knowledge
    datasets_dir: str = "datasets"
    processed_dir: str = "datasets/processed"
    knowledge_db_path: str = "datasets/processed/knowledge.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
