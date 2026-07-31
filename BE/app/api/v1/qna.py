from math import ceil
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, File, Query, UploadFile, status
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import DomainError
from app.models.auth import User
from app.models.qna import QnaComment, QnaImage, QnaPost
from app.schemas.common import SuccessResponse
from app.schemas.qna import (
    QnaCommentCreateRequest,
    QnaCommentUpdateRequest,
    QnaPostCreateRequest,
    QnaPostUpdateRequest,
)

router = APIRouter(prefix="/qna", tags=["Q&A"])
QNA_UPLOAD_ROOT = Path("uploads/qna")


def get_post(db: DbSession, post_id: str) -> QnaPost:
    post = db.scalar(
        select(QnaPost).where(
            QnaPost.id == post_id,
            QnaPost.deleted.is_(False),
        )
    )
    if post is None:
        raise DomainError("QNA_POST_NOT_FOUND", "게시글을 찾을 수 없습니다.", 404)
    return post


def get_comment(db: DbSession, post_id: str, comment_id: str) -> QnaComment:
    comment = db.scalar(
        select(QnaComment).where(
            QnaComment.id == comment_id,
            QnaComment.post_id == post_id,
            QnaComment.deleted.is_(False),
        )
    )
    if comment is None:
        raise DomainError("QNA_COMMENT_NOT_FOUND", "댓글을 찾을 수 없습니다.", 404)
    return comment


def author_data(db: DbSession, author_id: str, anonymous: bool) -> dict[str, object]:
    if anonymous:
        return {"id": None, "name": "익명", "anonymous": True}
    user = db.get(User, author_id)
    return {
        "id": author_id,
        "name": user.name if user else "탈퇴한 사용자",
        "anonymous": False,
    }


def post_data(
    db: DbSession,
    post: QnaPost,
    *,
    comment_count: int | None = None,
) -> dict[str, object]:
    if comment_count is None:
        comment_count = db.scalar(
            select(func.count())
            .select_from(QnaComment)
            .where(
                QnaComment.post_id == post.id,
                QnaComment.deleted.is_(False),
            )
        ) or 0
    image_rows = (
        list(db.scalars(select(QnaImage).where(QnaImage.id.in_(post.image_ids))))
        if post.image_ids
        else []
    )
    image_map = {image.id: image for image in image_rows}
    return {
        "id": post.id,
        "category": post.category,
        "title": post.title,
        "content": post.content,
        "author": author_data(db, post.author_id, post.anonymous),
        "images": [
            {"imageId": image_id, "url": image_map[image_id].url}
            for image_id in post.image_ids
            if image_id in image_map
        ],
        "viewCount": post.view_count,
        "commentCount": comment_count,
        "createdAt": post.created_at,
        "updatedAt": post.updated_at,
    }


def validate_images(db: DbSession, user_id: str, image_ids: list[str]) -> None:
    if not image_ids:
        return
    count = db.scalar(
        select(func.count())
        .select_from(QnaImage)
        .where(
            QnaImage.id.in_(image_ids),
            QnaImage.owner_id == user_id,
        )
    )
    if count != len(set(image_ids)):
        raise DomainError(
            "QNA_IMAGE_NOT_FOUND",
            "본인이 업로드한 이미지만 첨부할 수 있습니다.",
            400,
        )


@router.get("/posts", response_model=SuccessResponse[dict[str, object]])
def list_posts(
    current_user: CurrentUser,
    db: DbSession,
    query: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=50),
    sort: str = Query(default="latest", pattern="^(latest|popular|unanswered)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> SuccessResponse[dict[str, object]]:
    _ = current_user
    comment_counts = (
        select(
            QnaComment.post_id,
            func.count(QnaComment.id).label("comment_count"),
        )
        .where(QnaComment.deleted.is_(False))
        .group_by(QnaComment.post_id)
        .subquery()
    )
    conditions = [QnaPost.deleted.is_(False)]
    if query:
        pattern = f"%{query.strip()}%"
        conditions.append(
            or_(QnaPost.title.ilike(pattern), QnaPost.content.ilike(pattern))
        )
    if category:
        conditions.append(QnaPost.category == category)
    comment_count = func.coalesce(comment_counts.c.comment_count, 0)
    if sort == "unanswered":
        conditions.append(comment_count == 0)
    order = (
        (QnaPost.view_count.desc(), QnaPost.created_at.desc())
        if sort == "popular"
        else (QnaPost.created_at.desc(),)
    )
    base = (
        select(QnaPost, comment_count)
        .outerjoin(comment_counts, comment_counts.c.post_id == QnaPost.id)
        .where(*conditions)
    )
    total = db.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0
    rows = db.execute(
        base.order_by(*order).offset((page - 1) * limit).limit(limit)
    ).all()
    total_pages = ceil(total / limit) if total else 0
    return SuccessResponse(
        data={
            "items": [
                post_data(db, post, comment_count=int(count))
                for post, count in rows
            ],
            "pagination": {
                "currentPage": page,
                "totalPages": total_pages,
                "totalItems": total,
                "hasNext": page < total_pages,
                "hasPrev": page > 1,
            },
        }
    )


@router.post(
    "/posts",
    response_model=SuccessResponse[dict[str, object]],
    status_code=status.HTTP_201_CREATED,
)
def create_post(
    payload: QnaPostCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, object]]:
    validate_images(db, current_user.id, payload.image_ids)
    post = QnaPost(
        author_id=current_user.id,
        category=payload.category,
        title=payload.title,
        content=payload.content,
        image_ids=payload.image_ids,
        anonymous=payload.anonymous,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return SuccessResponse(data=post_data(db, post))


@router.get("/posts/{post_id}", response_model=SuccessResponse[dict[str, object]])
def get_post_detail(
    post_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, object]]:
    _ = current_user
    post = get_post(db, post_id)
    post.view_count += 1
    comments = list(
        db.scalars(
            select(QnaComment)
            .where(
                QnaComment.post_id == post.id,
                QnaComment.deleted.is_(False),
            )
            .order_by(QnaComment.created_at.asc())
        )
    )
    db.commit()
    data = post_data(db, post, comment_count=len(comments))
    data["comments"] = [
        {
            "id": comment.id,
            "content": comment.content,
            "author": author_data(db, comment.author_id, comment.anonymous),
            "createdAt": comment.created_at,
            "updatedAt": comment.updated_at,
        }
        for comment in comments
    ]
    return SuccessResponse(data=data)


@router.patch("/posts/{post_id}", response_model=SuccessResponse[dict[str, object]])
def update_post(
    post_id: str,
    payload: QnaPostUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, object]]:
    post = get_post(db, post_id)
    if post.author_id != current_user.id:
        raise DomainError("FORBIDDEN", "작성자만 게시글을 수정할 수 있습니다.", 403)
    updates = payload.model_dump(exclude_unset=True)
    if "image_ids" in updates:
        validate_images(db, current_user.id, updates["image_ids"])
    for field, value in updates.items():
        setattr(post, field, value)
    db.commit()
    db.refresh(post)
    return SuccessResponse(data=post_data(db, post))


@router.delete(
    "/posts/{post_id}",
    response_model=SuccessResponse[dict[str, bool]],
)
def delete_post(
    post_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, bool]]:
    post = get_post(db, post_id)
    if post.author_id != current_user.id:
        raise DomainError("FORBIDDEN", "작성자만 게시글을 삭제할 수 있습니다.", 403)
    post.deleted = True
    db.commit()
    return SuccessResponse(data={"deleted": True})


@router.post(
    "/images",
    response_model=SuccessResponse[dict[str, object]],
    status_code=status.HTTP_201_CREATED,
)
async def upload_qna_image(
    current_user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File()],
) -> SuccessResponse[dict[str, object]]:
    original_name = file.filename or ""
    extension = Path(original_name).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise DomainError("INVALID_FILE_TYPE", "JPG, PNG, WEBP만 업로드할 수 있습니다.", 400)
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise DomainError("FILE_TOO_LARGE", "이미지는 최대 5MB까지 가능합니다.", 413)
    target_dir = QNA_UPLOAD_ROOT / current_user.id
    target_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    target = target_dir / stored_name
    target.write_bytes(content)
    image = QnaImage(
        owner_id=current_user.id,
        original_name=original_name,
        url=f"/uploads/qna/{current_user.id}/{stored_name}",
        size=len(content),
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return SuccessResponse(
        data={
            "imageId": image.id,
            "url": image.url,
            "fileName": image.original_name,
            "size": image.size,
        }
    )


@router.post(
    "/posts/{post_id}/comments",
    response_model=SuccessResponse[dict[str, object]],
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    post_id: str,
    payload: QnaCommentCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, object]]:
    post = get_post(db, post_id)
    comment = QnaComment(
        post_id=post.id,
        author_id=current_user.id,
        content=payload.content,
        anonymous=payload.anonymous,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return SuccessResponse(
        data={
            "id": comment.id,
            "postId": post.id,
            "content": comment.content,
            "author": author_data(db, comment.author_id, comment.anonymous),
            "createdAt": comment.created_at,
        }
    )


@router.patch(
    "/posts/{post_id}/comments/{comment_id}",
    response_model=SuccessResponse[dict[str, object]],
)
def update_comment(
    post_id: str,
    comment_id: str,
    payload: QnaCommentUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, object]]:
    get_post(db, post_id)
    comment = get_comment(db, post_id, comment_id)
    if comment.author_id != current_user.id:
        raise DomainError("FORBIDDEN", "작성자만 댓글을 수정할 수 있습니다.", 403)
    comment.content = payload.content
    if payload.anonymous is not None:
        comment.anonymous = payload.anonymous
    db.commit()
    db.refresh(comment)
    return SuccessResponse(
        data={
            "id": comment.id,
            "content": comment.content,
            "author": author_data(db, comment.author_id, comment.anonymous),
            "updatedAt": comment.updated_at,
        }
    )


@router.delete(
    "/posts/{post_id}/comments/{comment_id}",
    response_model=SuccessResponse[dict[str, bool]],
)
def delete_comment(
    post_id: str,
    comment_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, bool]]:
    get_post(db, post_id)
    comment = get_comment(db, post_id, comment_id)
    if comment.author_id != current_user.id:
        raise DomainError("FORBIDDEN", "작성자만 댓글을 삭제할 수 있습니다.", 403)
    comment.deleted = True
    db.commit()
    return SuccessResponse(data={"deleted": True})
