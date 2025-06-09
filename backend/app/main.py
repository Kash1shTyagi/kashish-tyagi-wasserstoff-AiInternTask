import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import configure_logging
from app.config import settings
from app.db.session import init_db, get_db

from app.api.v1.upload import router as upload_router
from app.api.v1.docs import router as docs_router
from app.api.v1.query import router as query_router
from app.api.v1.theme import router as theme_router

def create_app() -> FastAPI:
    configure_logging(log_to_file=True, logfile_path="logs/backend.log")
    logger = logging.getLogger(__name__)
    logger.info("Starting FastAPI application...")

    init_db()
    logger.info("Database tables verified/created.")

    app = FastAPI(
        title="Document Research & Theme Identification Chatbot Backend",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(upload_router, prefix="/api/v1/upload", tags=["upload"])
    app.include_router(docs_router, prefix="/api/v1/docs", tags=["documents"])
    app.include_router(query_router, prefix="/api/v1/query", tags=["query"])
    app.include_router(theme_router, prefix="/api/v1/theme", tags=["theme"])

    @app.get("/health", summary="Health check")
    async def health_check():
        return {"status": "ok"}

    return app

app = create_app()
