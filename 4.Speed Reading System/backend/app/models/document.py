"""Document model for storing uploaded/pasted text documents."""

from datetime import UTC, datetime
import uuid

from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import Language, SourceType


class Document(Base):
    """SQLAlchemy model for text documents."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True, index=True)

    title = Column(String(500), nullable=False)
    source_type = Column(SAEnum(SourceType), nullable=False)
    language = Column(SAEnum(Language), nullable=False)
    original_filename = Column(String(255), nullable=True)

    normalized_text = Column(Text, nullable=False)
    total_words = Column(Integer, nullable=False)
    tokenizer_version = Column(String(50), nullable=False, default="1.0.0")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    tokens = relationship("Token", back_populates="document", cascade="all, delete-orphan")
    sessions = relationship("ReadingSession", back_populates="document", cascade="all, delete-orphan")
