from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import ConsultationStatus


class ConsultationSession(TimestampMixin, Base):
    __tablename__ = "consultation_sessions"
    __table_args__ = (
        CheckConstraint(
            "refined_question_revision_count >= 0 AND refined_question_revision_count <= 3",
            name="ck_consultation_revision_count",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"ses_{uuid4()}",
    )
    mentee_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(40),
        default=ConsultationStatus.COLLECTING_CONTEXT,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    refined_question: Mapped[str | None] = mapped_column(Text)
    conversation_summary: Mapped[str | None] = mapped_column(Text)
    current_bottleneck: Mapped[str | None] = mapped_column(String(300))
    expected_answer_type: Mapped[str | None] = mapped_column(String(100))
    refined_question_revision_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    route: Mapped[str | None] = mapped_column(String(30), index=True)
    route_reason: Mapped[str | None] = mapped_column(Text)
    selected_persona_id: Mapped[str | None] = mapped_column(
        ForeignKey("mentor_personas.id", ondelete="SET NULL"),
        index=True,
    )
    selected_persona_version: Mapped[str | None] = mapped_column(String(30))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConsultationMessage(TimestampMixin, Base):
    __tablename__ = "consultation_messages"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"msg_{uuid4()}",
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("consultation_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class PersonaRecommendation(TimestampMixin, Base):
    __tablename__ = "persona_recommendations"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"rec_{uuid4()}",
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("consultation_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    persona_id: Mapped[str] = mapped_column(
        ForeignKey("mentor_personas.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    persona_version: Mapped[str] = mapped_column(String(30), nullable=False)


class ConsultationAgentContext(TimestampMixin, Base):
    __tablename__ = "consultation_agent_contexts"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("consultation_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    safe_context: Mapped[str] = mapped_column(Text, default="", nullable=False)
    search_query: Mapped[str] = mapped_column(Text, default="", nullable=False)
    match_query: Mapped[str] = mapped_column(Text, default="", nullable=False)
    question_units: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    taxonomy_tags: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    routing_hints: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    hard_case_flags: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    agent1_raw_output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    agent2_raw_output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
