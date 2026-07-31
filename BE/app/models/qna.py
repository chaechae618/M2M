from uuid import uuid4

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class QnaPost(TimestampMixin, Base):
    __tablename__ = "qna_posts"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"qna_{uuid4()}",
    )
    author_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)


class QnaComment(TimestampMixin, Base):
    __tablename__ = "qna_comments"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"cmt_{uuid4()}",
    )
    post_id: Mapped[str] = mapped_column(
        ForeignKey("qna_posts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    author_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)


class QnaImage(TimestampMixin, Base):
    __tablename__ = "qna_images"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"img_{uuid4()}",
    )
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
