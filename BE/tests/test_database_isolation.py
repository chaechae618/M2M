from pathlib import Path

from sqlalchemy import func, select

from app.api.v1.mentees import UPLOAD_ROOT
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.auth import User


def test_pytest_uses_isolated_database_and_upload_directory() -> None:
    settings = get_settings()
    database_path = Path(settings.database_url.removeprefix("sqlite:///"))

    assert settings.app_env == "test"
    assert database_path.name == "m2m-test.db"
    assert "m2m-pytest-" in str(database_path.parent)
    assert settings.upload_root == UPLOAD_ROOT
    assert "m2m-pytest-" in str(UPLOAD_ROOT)

    with SessionLocal() as db:
        user_count = db.scalar(select(func.count()).select_from(User))

    assert user_count == 0
