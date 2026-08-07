import hashlib
import secrets
from datetime import UTC, datetime, timedelta

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
from app.models.auth import PasswordResetToken, RefreshToken, User
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

    def request_password_reset(self, email: str) -> tuple[str | None, datetime | None]:
        user = self.db.scalar(select(User).where(User.email == email.lower()))
        if user is None or not user.is_active:
            return None, None

        now = datetime.now(UTC)
        existing_tokens = self.db.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        )
        for item in existing_tokens:
            item.used_at = now

        raw_token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(minutes=self.settings.password_reset_expire_minutes)
        self.db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=self._token_digest(raw_token),
                expires_at=expires_at,
            )
        )
        self.db.commit()
        return raw_token, expires_at

    def reset_password(self, token: str, new_password: str) -> User:
        now = datetime.now(UTC)
        reset_token = self.db.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == self._token_digest(token),
                PasswordResetToken.used_at.is_(None),
            )
        )
        if reset_token is None:
            raise DomainError(
                "INVALID_PASSWORD_RESET_TOKEN",
                "유효하지 않은 비밀번호 재설정 토큰입니다.",
                400,
            )

        expires_at = reset_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= now:
            reset_token.used_at = now
            self.db.commit()
            raise DomainError(
                "PASSWORD_RESET_TOKEN_EXPIRED",
                "비밀번호 재설정 토큰이 만료되었습니다.",
                400,
            )

        user = self.db.get(User, reset_token.user_id)
        if user is None or not user.is_active:
            raise DomainError("ACCOUNT_DISABLED", "사용할 수 없는 계정입니다.", 403)

        user.password_hash = hash_password(new_password)
        reset_token.used_at = now
        refresh_tokens = self.db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        for refresh_token in refresh_tokens:
            refresh_token.revoked_at = now
        self.db.commit()
        return user

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

    @staticmethod
    def _token_digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
