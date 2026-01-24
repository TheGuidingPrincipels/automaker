"""Reading session model for tracking reading progress."""

from datetime import UTC, datetime, timedelta
import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.config import get_settings
from app.database import Base


class ReadingSession(Base):
    """SQLAlchemy model for reading sessions."""

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)

    target_wpm = Column(Integer, nullable=False, default=300)
    ramp_enabled = Column(Boolean, nullable=False, default=True)
    ramp_seconds = Column(Integer, nullable=False, default=30)
    ramp_start_wpm = Column(Integer, nullable=True)

    current_word_index = Column(Integer, nullable=False, default=0)
    last_known_percent = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    expires_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
        + timedelta(days=get_settings().session_expiry_days),
    )

    document = relationship("Document", back_populates="sessions")
