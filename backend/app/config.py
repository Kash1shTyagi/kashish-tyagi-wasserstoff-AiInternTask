import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATA_DIR: str = os.getenv("DATA_DIR", "data/uploads")
    DATABASE_URL: str
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")

    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "tesseract")

    GROQ_API_KEY: str
    GROQ_MODEL_NAME: str = "llama3_70b_8192"

    GEMINI_API_KEY: str
    GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

    DEFAULT_LLM_BACKEND: str = os.getenv("DEFAULT_LLM_BACKEND", "groq")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
