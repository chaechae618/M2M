from io import BytesIO
from pathlib import Path
from typing import Annotated
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
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
UPLOAD_ROOT = get_settings().upload_root
FILE_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


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
        resumeFileName=profile.resume_file_name,
        portfolioUrl=profile.portfolio_url,
        portfolioFileName=profile.portfolio_file_name,
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
    original_name = Path(file.filename or "").name
    if not original_name or len(original_name) > 255:
        raise DomainError("INVALID_FILE_NAME", "파일 이름을 확인해주세요.", 400)
    extension = Path(original_name).suffix.lower()
    if extension not in allowed_extensions:
        raise DomainError(
            "INVALID_FILE_TYPE",
            f"허용되는 파일 형식은 {', '.join(sorted(allowed_extensions))}입니다.",
            400,
        )

    content = await file.read(max_size + 1)
    if not content:
        raise DomainError("EMPTY_FILE", "비어 있는 파일은 업로드할 수 없습니다.", 400)
    if len(content) > max_size:
        raise DomainError("FILE_TOO_LARGE", "파일 용량 제한을 초과했습니다.", 413)
    validate_file_content(content, extension)

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
        contentType=FILE_MEDIA_TYPES[extension],
    )


def validate_file_content(content: bytes, extension: str) -> None:
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise DomainError("INVALID_FILE_CONTENT", "올바른 PDF 파일이 아닙니다.", 400)
    if extension == ".pptx":
        try:
            with ZipFile(BytesIO(content)) as archive:
                names = set(archive.namelist())
        except BadZipFile as exc:
            raise DomainError(
                "INVALID_FILE_CONTENT",
                "올바른 PPTX 파일이 아닙니다.",
                400,
            ) from exc
        if "[Content_Types].xml" not in names or not any(
            name.startswith("ppt/") for name in names
        ):
            raise DomainError("INVALID_FILE_CONTENT", "올바른 PPTX 파일이 아닙니다.", 400)


def stored_upload_path(url: str | None, user_id: str) -> Path | None:
    if not url or not url.startswith(f"/uploads/{user_id}/"):
        return None
    relative_path = Path(url.removeprefix("/uploads/"))
    candidate = (UPLOAD_ROOT / relative_path).resolve()
    user_root = (UPLOAD_ROOT / user_id).resolve()
    return candidate if candidate.is_relative_to(user_root) else None


def remove_stored_upload(url: str | None, user_id: str) -> bool:
    path = stored_upload_path(url, user_id)
    if path is None or not path.is_file():
        return False
    path.unlink()
    return True


def profile_file_response(
    url: str | None,
    file_name: str | None,
    user_id: str,
) -> FileResponse:
    path = stored_upload_path(url, user_id)
    if path is None or not path.is_file():
        raise DomainError("FILE_NOT_FOUND", "등록된 파일을 찾을 수 없습니다.", 404)
    return FileResponse(
        path,
        filename=file_name or path.name,
        media_type=FILE_MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream"),
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
        {".pdf"},
        10 * 1024 * 1024,
    )
    profile = MenteeService(db, current_user).get_profile()
    previous_url = profile.resume_url
    profile.resume_url = result.url
    profile.resume_file_name = result.file_name
    db.commit()
    remove_stored_upload(previous_url, current_user.id)
    return SuccessResponse(data=result)


@router.get("/resume/file", response_class=FileResponse)
def download_resume(current_user: CurrentUser, db: DbSession) -> FileResponse:
    profile = MenteeService(db, current_user).get_profile()
    return profile_file_response(
        profile.resume_url,
        profile.resume_file_name,
        current_user.id,
    )


@router.delete("/resume", response_model=SuccessResponse[dict[str, object]])
def delete_resume(
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, object]]:
    profile = MenteeService(db, current_user).get_profile()
    previous_url = profile.resume_url
    profile.resume_url = None
    profile.resume_file_name = None
    db.commit()
    removed = remove_stored_upload(previous_url, current_user.id)
    return SuccessResponse(data={"fileType": "resume", "deleted": True, "fileRemoved": removed})


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
    previous_url = profile.portfolio_url
    profile.portfolio_url = result.url
    profile.portfolio_file_name = result.file_name
    db.commit()
    remove_stored_upload(previous_url, current_user.id)
    return SuccessResponse(data=result)


@router.get("/portfolio/file", response_class=FileResponse)
def download_portfolio(current_user: CurrentUser, db: DbSession) -> FileResponse:
    profile = MenteeService(db, current_user).get_profile()
    return profile_file_response(
        profile.portfolio_url,
        profile.portfolio_file_name,
        current_user.id,
    )


@router.delete("/portfolio", response_model=SuccessResponse[dict[str, object]])
def delete_portfolio(
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, object]]:
    profile = MenteeService(db, current_user).get_profile()
    previous_url = profile.portfolio_url
    profile.portfolio_url = None
    profile.portfolio_file_name = None
    db.commit()
    removed = remove_stored_upload(previous_url, current_user.id)
    return SuccessResponse(data={"fileType": "portfolio", "deleted": True, "fileRemoved": removed})


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
