from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import JobStatus


class AsyncJob(TimestampMixin, Base):
    __tablename__ = "async_jobs"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"job_{uuid4()}",
    )
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("consultation_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=JobStatus.QUEUED,
        index=True,
        nullable=False,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(100))
    result_url: Mapped[str | None] = mapped_column(String(1000))
    error: Mapped[dict | None] = mapped_column(JSON)
