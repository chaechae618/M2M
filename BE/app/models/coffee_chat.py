from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import CoffeeChatStatus


class CoffeeChatRequest(TimestampMixin, Base):
    __tablename__ = "coffee_chat_requests"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"cfr_{uuid4()}",
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("consultation_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    mentee_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    persona_id: Mapped[str] = mapped_column(
        ForeignKey("mentor_personas.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    request_message: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20),
        default=CoffeeChatStatus.REQUESTED,
        index=True,
        nullable=False,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
