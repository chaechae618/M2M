from uuid import uuid4

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MentorPersona(TimestampMixin, Base):
    __tablename__ = "mentor_personas"

    id: Mapped[str] = mapped_column(
        String(80),
        primary_key=True,
        default=lambda: f"persona_{uuid4()}",
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    current_role: Mapped[str] = mapped_column(String(200), nullable=False)
    years_of_experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    career_history: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    expertise: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    profile_summary: Mapped[str] = mapped_column(Text, nullable=False)
    answer_style: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    matching_summary: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
