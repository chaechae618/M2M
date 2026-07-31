from fastapi import APIRouter, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    TokenPairResponse,
    UserResponse,
)
from app.schemas.common import SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def to_user_response(user: object) -> UserResponse:
    return UserResponse(
        id=user.id,
        role=user.role,
        email=user.email,
        name=user.name,
        profileCompleted=user.profile is not None,
        createdAt=user.created_at,
    )


@router.post(
    "/signup",
    response_model=SuccessResponse[TokenPairResponse],
    status_code=status.HTTP_201_CREATED,
)
def signup(
    payload: SignupRequest,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[TokenPairResponse]:
    user, access_token, refresh_token = AuthService(db, settings).signup(payload)
    return SuccessResponse(
        data=TokenPairResponse(
            user=to_user_response(user),
            accessToken=access_token,
            refreshToken=refresh_token,
            expiresIn=settings.access_token_expire_minutes * 60,
        )
    )


@router.post("/login", response_model=SuccessResponse[TokenPairResponse])
def login(
    payload: LoginRequest,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[TokenPairResponse]:
    user, access_token, refresh_token = AuthService(db, settings).login(
        str(payload.email),
        payload.password,
    )
    return SuccessResponse(
        data=TokenPairResponse(
            user=to_user_response(user),
            accessToken=access_token,
            refreshToken=refresh_token,
            expiresIn=settings.access_token_expire_minutes * 60,
        )
    )


@router.post("/refresh", response_model=SuccessResponse[AccessTokenResponse])
def refresh(
    payload: RefreshRequest,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[AccessTokenResponse]:
    access_token, refresh_token = AuthService(db, settings).refresh(payload.refresh_token)
    return SuccessResponse(
        data=AccessTokenResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            expiresIn=settings.access_token_expire_minutes * 60,
        )
    )


@router.post("/logout", response_model=SuccessResponse[dict[str, bool]])
def logout(
    payload: LogoutRequest,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, bool]]:
    AuthService(db, settings).logout(payload.refresh_token, current_user.id)
    return SuccessResponse(data={"loggedOut": True}, message="로그아웃했습니다.")


@router.get("/me", response_model=SuccessResponse[UserResponse])
def me(current_user: CurrentUser) -> SuccessResponse[UserResponse]:
    return SuccessResponse(data=to_user_response(current_user))
