from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import Settings
from app.core.exceptions import DomainError

password_hash = PasswordHash.recommended()


@dataclass(frozen=True)
class TokenPayload:
    subject: str
    token_type: str
    jti: str
    expires_at: datetime


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_token(
    *,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    settings: Settings,
) -> tuple[str, str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + expires_delta
    jti = str(uuid4())
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expires_at


def create_access_token(subject: str, settings: Settings) -> tuple[str, str, datetime]:
    return create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        settings=settings,
    )


def create_refresh_token(subject: str, settings: Settings) -> tuple[str, str, datetime]:
    return create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        settings=settings,
    )


def decode_token(token: str, expected_type: str, settings: Settings) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise DomainError("INVALID_TOKEN", "유효하지 않은 토큰입니다.", 401) from exc

    subject = payload.get("sub")
    token_type = payload.get("type")
    jti = payload.get("jti")
    expires_at = payload.get("exp")
    if not subject or not jti or token_type != expected_type or expires_at is None:
        raise DomainError("INVALID_TOKEN", "유효하지 않은 토큰입니다.", 401)

    return TokenPayload(
        subject=str(subject),
        token_type=str(token_type),
        jti=str(jti),
        expires_at=datetime.fromtimestamp(float(expires_at), tz=UTC),
    )
