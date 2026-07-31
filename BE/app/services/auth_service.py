from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import DomainError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.auth import RefreshToken, User
from app.models.mentee import MenteeProfile
from app.schemas.auth import SignupRequest


class AuthService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def signup(self, payload: SignupRequest) -> tuple[User, str, str]:
        email = payload.email.lower()
        existing = self.db.scalar(select(User).where(User.email == email))
        if existing:
            raise DomainError("EMAIL_EXISTS", "이미 가입된 이메일입니다.", 409)

        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            name=payload.name.strip(),
        )
        user.profile = MenteeProfile(
            current_status=payload.current_status,
            target_roles=payload.target_roles,
            interest_domains=payload.interest_domains,
        )
        self.db.add(user)
        self.db.flush()

        access_token, _, _ = create_access_token(user.id, self.settings)
        refresh_token = self._issue_refresh_token(user.id)
        self.db.commit()
        self.db.refresh(user)
        return user, access_token, refresh_token

    def login(self, email: str, password: str) -> tuple[User, str, str]:
        user = self.db.scalar(select(User).where(User.email == email.lower()))
        if not user or not verify_password(password, user.password_hash):
            raise DomainError(
                "INVALID_CREDENTIALS",
                "이메일 또는 비밀번호가 올바르지 않습니다.",
                401,
            )
        if not user.is_active:
            raise DomainError("ACCOUNT_DISABLED", "비활성화된 계정입니다.", 403)

        access_token, _, _ = create_access_token(user.id, self.settings)
        refresh_token = self._issue_refresh_token(user.id)
        self.db.commit()
        return user, access_token, refresh_token

    def refresh(self, token: str) -> tuple[str, str]:
        payload = decode_token(token, "refresh", self.settings)
        stored = self.db.scalar(select(RefreshToken).where(RefreshToken.token_jti == payload.jti))
        if not stored or stored.revoked_at is not None:
            raise DomainError("INVALID_TOKEN", "유효하지 않은 토큰입니다.", 401)

        user = self.db.get(User, payload.subject)
        if not user or not user.is_active:
            raise DomainError("UNAUTHORIZED", "인증이 필요합니다.", 401)

        stored.revoked_at = datetime.now(UTC)
        access_token, _, _ = create_access_token(user.id, self.settings)
        refresh_token = self._issue_refresh_token(user.id)
        self.db.commit()
        return access_token, refresh_token

    def logout(self, token: str, current_user_id: str) -> None:
        payload = decode_token(token, "refresh", self.settings)
        if payload.subject != current_user_id:
            raise DomainError("FORBIDDEN", "다른 사용자의 토큰을 폐기할 수 없습니다.", 403)

        stored = self.db.scalar(select(RefreshToken).where(RefreshToken.token_jti == payload.jti))
        if stored and stored.revoked_at is None:
            stored.revoked_at = datetime.now(UTC)
            self.db.commit()

    def _issue_refresh_token(self, user_id: str) -> str:
        token, jti, expires_at = create_refresh_token(user_id, self.settings)
        self.db.add(
            RefreshToken(
                user_id=user_id,
                token_jti=jti,
                expires_at=expires_at,
            )
        )
        return token
