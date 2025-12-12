"""
Main FastAPI application with modular architecture.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.config import get_settings
from app.routes import chat_router
from app.core.providers import registry
from app.core.exceptions import AppException
from app.database import init_db, close_db

# Import providers to register them
import app.providers  # noqa: F401


# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment.value}")
    logger.info(f"Default LLM Provider: {settings.default_llm_provider}")

    # Initialize database
    logger.info("📦 Initializing database...")
    await init_db()
    logger.info("✅ Database initialized")

    yield

    # Shutdown
    logger.info("👋 Shutting down...")
    await registry.cleanup_all()
    await close_db()
    logger.info("✅ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI-powered investor finder chatbot for entrepreneurs. Find US-based investors for your startup with modular and extensible architecture.",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)


# Exception handler for custom exceptions
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application-specific exceptions."""
    logger.error(f"Application error: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=500,
        content=exc.to_dict()
    )


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(chat_router)


# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Serve the main page."""
    return FileResponse("static/index.html")


@app.get("/info")
async def app_info():
    """Get application information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment.value,
        "available_providers": {
            "llm": registry.list_providers("llm"),
            "search": registry.list_providers("search"),
            "scraper": registry.list_providers("scraper")
        },
        "default_llm": settings.default_llm_provider
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
