from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import DomainError
from app.schemas.common import SuccessResponse
from app.schemas.mentee import (
    ExperienceCreateRequest,
    ExperienceResponse,
    ExperienceUpdateRequest,
    FileUploadResponse,
    MenteeProfileResponse,
    MenteeProfileUpdateRequest,
)
from app.services.mentee_service import MenteeService

router = APIRouter(prefix="/mentees/me", tags=["Mentees"])
UPLOAD_ROOT = Path("uploads")


def to_profile_response(user: object, profile: object) -> MenteeProfileResponse:
    return MenteeProfileResponse(
        id=profile.id,
        email=user.email,
        name=user.name,
        currentStatus=profile.current_status,
        background=profile.background,
        consideringOptions=profile.considering_options,
        targetRoles=profile.target_roles,
        interestDomains=profile.interest_domains,
        resumeUrl=profile.resume_url,
        portfolioUrl=profile.portfolio_url,
        updatedAt=profile.updated_at,
    )


@router.get("", response_model=SuccessResponse[MenteeProfileResponse])
def get_profile(
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[MenteeProfileResponse]:
    profile = MenteeService(db, current_user).get_profile()
    return SuccessResponse(data=to_profile_response(current_user, profile))


@router.patch("", response_model=SuccessResponse[MenteeProfileResponse])
def update_profile(
    payload: MenteeProfileUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[MenteeProfileResponse]:
    service = MenteeService(db, current_user)
    profile = service.get_profile()
    updates = payload.model_dump(exclude_unset=True)
    name = updates.pop("name", None)
    if name is not None:
        current_user.name = name.strip()
    for field, value in updates.items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return SuccessResponse(data=to_profile_response(current_user, profile))


async def save_upload(
    file: UploadFile,
    user_id: str,
    file_type: str,
    allowed_extensions: set[str],
    max_size: int,
) -> FileUploadResponse:
    original_name = file.filename or ""
    extension = Path(original_name).suffix.lower()
    if extension not in allowed_extensions:
        raise DomainError(
            "INVALID_FILE_TYPE",
            f"허용되는 파일 형식은 {', '.join(sorted(allowed_extensions))}입니다.",
            400,
        )

    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise DomainError("FILE_TOO_LARGE", "파일 용량 제한을 초과했습니다.", 413)

    target_dir = UPLOAD_ROOT / user_id
    target_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{file_type}_{uuid4().hex}{extension}"
    target = target_dir / stored_name
    target.write_bytes(content)
    return FileUploadResponse(
        fileType=file_type,
        fileName=original_name,
        url=f"/uploads/{user_id}/{stored_name}",
        size=len(content),
    )


@router.post("/resume", response_model=SuccessResponse[FileUploadResponse])
async def upload_resume(
    current_user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File()],
) -> SuccessResponse[FileUploadResponse]:
    result = await save_upload(
        file,
        current_user.id,
        "resume",
        {".pdf", ".docx"},
        10 * 1024 * 1024,
    )
    profile = MenteeService(db, current_user).get_profile()
    profile.resume_url = result.url
    db.commit()
    return SuccessResponse(data=result)


@router.post("/portfolio", response_model=SuccessResponse[FileUploadResponse])
async def upload_portfolio(
    current_user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File()],
) -> SuccessResponse[FileUploadResponse]:
    result = await save_upload(
        file,
        current_user.id,
        "portfolio",
        {".pdf", ".pptx"},
        20 * 1024 * 1024,
    )
    profile = MenteeService(db, current_user).get_profile()
    profile.portfolio_url = result.url
    db.commit()
    return SuccessResponse(data=result)


@router.get("/experiences", response_model=SuccessResponse[list[ExperienceResponse]])
def list_experiences(
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[list[ExperienceResponse]]:
    experiences = MenteeService(db, current_user).list_experiences()
    return SuccessResponse(data=[ExperienceResponse.model_validate(item) for item in experiences])


@router.post(
    "/experiences",
    response_model=SuccessResponse[ExperienceResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_experience(
    payload: ExperienceCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[ExperienceResponse]:
    experience = MenteeService(db, current_user).create_experience(payload)
    return SuccessResponse(data=ExperienceResponse.model_validate(experience))


@router.patch(
    "/experiences/{experience_id}",
    response_model=SuccessResponse[ExperienceResponse],
)
def update_experience(
    experience_id: str,
    payload: ExperienceUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[ExperienceResponse]:
    experience = MenteeService(db, current_user).update_experience(experience_id, payload)
    return SuccessResponse(data=ExperienceResponse.model_validate(experience))


@router.delete(
    "/experiences/{experience_id}",
    response_model=SuccessResponse[dict[str, bool]],
)
def delete_experience(
    experience_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, bool]]:
    MenteeService(db, current_user).delete_experience(experience_id)
    return SuccessResponse(data={"deleted": True}, message="경험을 삭제했습니다.")
