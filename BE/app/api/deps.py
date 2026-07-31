from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import DomainError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.auth import User

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
    settings: AppSettings,
) -> User:
    if credentials is None:
        raise DomainError("UNAUTHORIZED", "로그인이 필요합니다.", 401)

    payload = decode_token(credentials.credentials, "access", settings)
    user = db.get(User, payload.subject)
    if not user or not user.is_active:
        raise DomainError("UNAUTHORIZED", "로그인이 필요합니다.", 401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
