from app.core.config import get_settings
from app.core.exceptions import DomainError

UPLOAD_ROOT = get_settings().upload_root


def delete_uploaded_file(url: str | None) -> bool:
    if not url:
        return False
    prefix = "/uploads/"
    if not url.startswith(prefix):
        raise DomainError("INVALID_UPLOAD_PATH", "삭제할 수 없는 업로드 경로입니다.", 400)

    root = UPLOAD_ROOT.resolve()
    target = (root / url.removeprefix(prefix)).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise DomainError("INVALID_UPLOAD_PATH", "삭제할 수 없는 업로드 경로입니다.", 400) from exc

    if not target.is_file():
        return False
    target.unlink()
    return True
