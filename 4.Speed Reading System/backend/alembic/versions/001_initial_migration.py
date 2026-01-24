"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2024-01-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_type", sa.Enum("paste", "md", "pdf", name="sourcetype"), nullable=False),
        sa.Column("language", sa.Enum("en", "de", name="language"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("total_words", sa.Integer(), nullable=False),
        sa.Column(
            "tokenizer_version",
            sa.String(length=50),
            nullable=False,
            server_default="1.0.0",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_user_id"), "documents", ["user_id"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("target_wpm", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("ramp_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("ramp_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("ramp_start_wpm", sa.Integer(), nullable=True),
        sa.Column("current_word_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_known_percent", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sessions_document_id"), "sessions", ["document_id"], unique=False)
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)

    op.create_table(
        "tokens",
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("word_index", sa.Integer(), nullable=False),
        sa.Column("display_text", sa.String(length=500), nullable=False),
        sa.Column("clean_text", sa.String(length=500), nullable=False),
        sa.Column("orp_index_display", sa.Integer(), nullable=False),
        sa.Column(
            "delay_multiplier_after",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column("break_before", sa.Enum("paragraph", "heading", name="breaktype"), nullable=True),
        sa.Column("is_sentence_start", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_paragraph_start", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("char_offset_start", sa.Integer(), nullable=True),
        sa.Column("char_offset_end", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "word_index"),
    )
    op.create_index("ix_tokens_document_word", "tokens", ["document_id", "word_index"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tokens_document_word", table_name="tokens")
    op.drop_table("tokens")

    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_document_id"), table_name="sessions")
    op.drop_table("sessions")

    op.drop_index(op.f("ix_documents_user_id"), table_name="documents")
    op.drop_table("documents")

    op.execute("DROP TYPE IF EXISTS breaktype")
    op.execute("DROP TYPE IF EXISTS language")
    op.execute("DROP TYPE IF EXISTS sourcetype")
