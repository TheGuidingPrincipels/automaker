"""Token model for storing word-level tokens for RSVP reading."""

from sqlalchemy import (
    Boolean,
    Column,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import BreakType


class Token(Base):
    """SQLAlchemy model for word-level tokens."""

    __tablename__ = "tokens"

    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    word_index = Column(Integer, primary_key=True, nullable=False)

    display_text = Column(String(500), nullable=False)
    clean_text = Column(String(500), nullable=False)
    orp_index_display = Column(Integer, nullable=False)

    delay_multiplier_after = Column(Float, nullable=False, default=1.0)
    break_before = Column(SAEnum(BreakType), nullable=True)

    is_sentence_start = Column(Boolean, nullable=False, default=False)
    is_paragraph_start = Column(Boolean, nullable=False, default=False)

    char_offset_start = Column(Integer, nullable=True)
    char_offset_end = Column(Integer, nullable=True)

    document = relationship("Document", back_populates="tokens")

    __table_args__ = (Index("ix_tokens_document_word", "document_id", "word_index"),)
