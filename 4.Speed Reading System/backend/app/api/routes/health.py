"""Health check API route."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    """Health check endpoint."""
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        logger.exception("Health check DB query failed")
        db_connected = False

    return {
        "status": "ok" if db_connected else "degraded",
        "database": "connected" if db_connected else "unavailable",
        "version": "0.1.0",
    }
