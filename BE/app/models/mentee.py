from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class MenteeProfile(TimestampMixin, Base):
    __tablename__ = "mentee_profiles"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"mte_{uuid4()}",
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    current_status: Mapped[str] = mapped_column(String(30), nullable=False)
    background: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    considering_options: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    target_roles: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    interest_domains: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    resume_url: Mapped[str | None] = mapped_column(String(1000))
    portfolio_url: Mapped[str | None] = mapped_column(String(1000))

    user: Mapped["User"] = relationship(back_populates="profile")  # noqa: F821


class MenteeExperience(TimestampMixin, Base):
    __tablename__ = "mentee_experiences"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"exp_{uuid4()}",
    )
    mentee_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    experience_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    organization: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[str | None] = mapped_column(String(7))
    end_date: Mapped[str | None] = mapped_column(String(7))
    role: Mapped[str | None] = mapped_column(String(200))
    key_skills: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    tools: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
