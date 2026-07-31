from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

CurrentStatus = Literal["student", "job_seeker", "career_change", "employed", "other"]


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=2, max_length=50)
    current_status: CurrentStatus = Field(alias="currentStatus")
    target_roles: list[str] = Field(default_factory=list, alias="targetRoles", max_length=10)
    interest_domains: list[str] = Field(
        default_factory=list,
        alias="interestDomains",
        max_length=10,
    )
    terms_consent: bool = Field(alias="termsConsent")
    privacy_consent: bool = Field(alias="privacyConsent")

    model_config = {"populate_by_name": True}

    @field_validator("terms_consent")
    @classmethod
    def require_terms_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("이용약관 동의가 필요합니다.")
        return value

    @field_validator("privacy_consent")
    @classmethod
    def require_privacy_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("개인정보 수집 동의가 필요합니다.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(alias="refreshToken")

    model_config = {"populate_by_name": True}


class LogoutRequest(BaseModel):
    refresh_token: str = Field(alias="refreshToken")

    model_config = {"populate_by_name": True}


class UserResponse(BaseModel):
    id: str
    role: str
    email: EmailStr
    name: str
    profile_completed: bool = Field(alias="profileCompleted")
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class TokenPairResponse(BaseModel):
    user: UserResponse
    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    expires_in: int = Field(alias="expiresIn")

    model_config = {"populate_by_name": True}


class AccessTokenResponse(BaseModel):
    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    expires_in: int = Field(alias="expiresIn")

    model_config = {"populate_by_name": True}
