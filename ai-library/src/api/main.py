# src/api/main.py
"""FastAPI application entry point."""

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .dependencies import get_config_sync, cleanup_dependencies
from .routes import sessions, library, query

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    # Startup
    yield
    # Shutdown
    await cleanup_dependencies()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance with routes, middleware, and error handlers.
    """
    config = get_config_sync()

    app = FastAPI(
        title="Knowledge Library API",
        description="REST API for the Knowledge Library system",
        version="0.1.0",
        lifespan=lifespan,
        debug=config.api.debug,
    )

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        error_id = str(uuid.uuid4())[:8]
        logger.exception("Unhandled exception [%s]: %s", error_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "error_id": error_id},
        )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_credentials=True,
        allow_methods=config.api.cors_methods,
        allow_headers=config.api.cors_headers,
    )

    # Include routers
    app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
    app.include_router(library.router, prefix="/api/library", tags=["library"])
    app.include_router(query.router, prefix="/api/query", tags=["query"])

    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": "0.1.0",
        }

    @app.get("/api", tags=["root"])
    async def api_root():
        """API root endpoint."""
        return {
            "name": "Knowledge Library API",
            "version": "0.1.0",
            "endpoints": {
                "sessions": "/api/sessions",
                "library": "/api/library",
                "query": "/api/query",
                "health": "/health",
            },
        }

    return app


# Default app instance for uvicorn
app = create_app()
