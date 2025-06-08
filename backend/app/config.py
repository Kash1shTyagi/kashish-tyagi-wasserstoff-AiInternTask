import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    DATA_DIR: str = os.getenv("DATA_DIR", "data/uploads")
    DATABASE_URL: str
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")

    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", r"C:/Program Files/Tesseract-OCR/tesseract.exe")

    GROQ_API_KEY: str
    GROQ_MODEL_NAME: str = "llama3_70b_8192"

    GEMINI_PROJECT_ID: str
    GEMINI_REGION: str = os.getenv("GEMINI_REGION", "us-central1")
    GEMINI_MODEL_ID: str = "gemini-pro"

    DEFAULT_LLM_BACKEND: str = os.getenv("DEFAULT_LLM_BACKEND", "groq")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
