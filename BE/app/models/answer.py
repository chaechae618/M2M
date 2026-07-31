from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Answer(TimestampMixin, Base):
    __tablename__ = "answers"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"ans_{uuid4()}",
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("consultation_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    answer_type: Mapped[str] = mapped_column(String(30), nullable=False)
    route: Mapped[str] = mapped_column(String(30), nullable=False)
    persona_id: Mapped[str | None] = mapped_column(
        ForeignKey("mentor_personas.id", ondelete="SET NULL"),
        index=True,
    )
    persona_version: Mapped[str | None] = mapped_column(String(30))
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    final_content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    source_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class Feedback(TimestampMixin, Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"fbk_{uuid4()}",
    )
    answer_id: Mapped[str] = mapped_column(
        ForeignKey("answers.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    mentee_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(nullable=False)
    helpful_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)


class ReuseConsent(TimestampMixin, Base):
    __tablename__ = "reuse_consents"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"cns_{uuid4()}",
    )
    answer_id: Mapped[str] = mapped_column(
        ForeignKey("answers.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    mentee_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    consent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    scope: Mapped[str] = mapped_column(String(50), default="anonymized_rag", nullable=False)
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AnswerAsset(TimestampMixin, Base):
    __tablename__ = "answer_assets"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"ast_{uuid4()}",
    )
    answer_id: Mapped[str] = mapped_column(
        ForeignKey("answers.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("consultation_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    anonymized_question: Mapped[str] = mapped_column(Text, nullable=False)
    anonymized_answer: Mapped[str] = mapped_column(Text, nullable=False)
    privacy_check_status: Mapped[str] = mapped_column(String(30), nullable=False)
    quality_check_status: Mapped[str] = mapped_column(String(30), nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AnswerAssetEmbedding(TimestampMixin, Base):
    __tablename__ = "answer_asset_embeddings"

    asset_id: Mapped[str] = mapped_column(
        ForeignKey("answer_assets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    vector: Mapped[list] = mapped_column(JSON, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
