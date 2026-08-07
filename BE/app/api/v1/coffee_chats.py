from datetime import UTC, datetime

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.core.exceptions import DomainError
from app.models.coffee_chat import CoffeeChatRequest
from app.models.consultation import PersonaRecommendation
from app.models.enums import CoffeeChatStatus, ConsultationStatus
from app.models.persona import MentorPersona
from app.schemas.coffee_chat import CoffeeChatCreateRequest, CoffeeChatUpdateRequest
from app.schemas.common import SuccessResponse
from app.services.consultation_service import ConsultationService

router = APIRouter(tags=["Coffee Chats"])


def get_owned_request(
    db: DbSession,
    request_id: str,
    mentee_id: str,
) -> CoffeeChatRequest:
    request = db.scalar(
        select(CoffeeChatRequest).where(
            CoffeeChatRequest.id == request_id,
            CoffeeChatRequest.mentee_id == mentee_id,
        )
    )
    if request is None:
        raise DomainError("COFFEE_CHAT_NOT_FOUND", "커피챗 요청을 찾을 수 없습니다.", 404)
    return request


def ensure_recommended_persona(
    db: DbSession,
    session_id: str,
    persona_id: str,
) -> MentorPersona:
    recommendation = db.scalar(
        select(PersonaRecommendation).where(
            PersonaRecommendation.session_id == session_id,
            PersonaRecommendation.persona_id == persona_id,
        )
    )
    persona = db.get(MentorPersona, persona_id)
    if recommendation is None or persona is None or not persona.active:
        raise DomainError(
            "PERSONA_NOT_RECOMMENDED",
            "해당 상담에서 추천된 Top 3 페르소나만 요청할 수 있습니다.",
            400,
        )
    return persona


def request_data(request: CoffeeChatRequest, persona: MentorPersona | None) -> dict[str, object]:
    return {
        "requestId": request.id,
        "sessionId": request.session_id,
        "persona": {
            "personaId": request.persona_id,
            "displayName": persona.display_name if persona else "AI 멘토",
            "isAiPersona": True,
        },
        "requestMessage": request.request_message,
        "preferredAt": request.preferred_at,
        "status": request.status,
        "acceptedAt": request.accepted_at,
        "completedAt": request.completed_at,
        "cancelledAt": request.cancelled_at,
        "createdAt": request.created_at,
        "updatedAt": request.updated_at,
    }


@router.post(
    "/consultations/{session_id}/coffee-chat-requests",
    response_model=SuccessResponse[dict[str, object]],
    status_code=status.HTTP_201_CREATED,
)
def create_coffee_chat_request(
    session_id: str,
    payload: CoffeeChatCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    session = ConsultationService(db, current_user, settings).get_owned(session_id)
    if session.status != ConsultationStatus.PERSONA_RECOMMENDED:
        raise DomainError(
            "INVALID_SESSION_STATE",
            "페르소나 Top 3 추천이 완료된 상담에서만 요청할 수 있습니다.",
            409,
        )
    persona = ensure_recommended_persona(db, session.id, payload.persona_id)
    active_request = db.scalar(
        select(CoffeeChatRequest).where(
            CoffeeChatRequest.session_id == session.id,
            CoffeeChatRequest.status.in_(
                [CoffeeChatStatus.REQUESTED, CoffeeChatStatus.ACCEPTED]
            ),
        )
    )
    if active_request is not None:
        raise DomainError(
            "COFFEE_CHAT_ALREADY_REQUESTED",
            "이 상담에는 이미 진행 중인 커피챗 요청이 있습니다.",
            409,
        )

    request = CoffeeChatRequest(
        session_id=session.id,
        mentee_id=current_user.id,
        persona_id=persona.id,
        request_message=payload.request_message.strip(),
        preferred_at=payload.preferred_at,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return SuccessResponse(
        data=request_data(request, persona),
        message="AI 멘토 페르소나에게 커피챗을 요청했습니다.",
    )


@router.get(
    "/coffee-chat-requests",
    response_model=SuccessResponse[list[dict[str, object]]],
)
def list_coffee_chat_requests(
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[list[dict[str, object]]]:
    requests = list(
        db.scalars(
            select(CoffeeChatRequest)
            .where(CoffeeChatRequest.mentee_id == current_user.id)
            .order_by(CoffeeChatRequest.created_at.desc())
        )
    )
    return SuccessResponse(
        data=[request_data(item, db.get(MentorPersona, item.persona_id)) for item in requests]
    )


@router.get(
    "/coffee-chat-requests/{request_id}",
    response_model=SuccessResponse[dict[str, object]],
)
def get_coffee_chat_request(
    request_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, object]]:
    request = get_owned_request(db, request_id, current_user.id)
    return SuccessResponse(
        data=request_data(request, db.get(MentorPersona, request.persona_id))
    )


@router.patch(
    "/coffee-chat-requests/{request_id}",
    response_model=SuccessResponse[dict[str, object]],
)
def update_coffee_chat_request(
    request_id: str,
    payload: CoffeeChatUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, object]]:
    request = get_owned_request(db, request_id, current_user.id)
    if request.status != CoffeeChatStatus.REQUESTED:
        raise DomainError(
            "COFFEE_CHAT_NOT_EDITABLE",
            "수락되거나 종료된 커피챗 요청은 수정할 수 없습니다.",
            409,
        )

    updates = payload.model_dump(exclude_unset=True)
    if "persona_id" in updates:
        ensure_recommended_persona(db, request.session_id, updates["persona_id"])
    for field, value in updates.items():
        setattr(request, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(request)
    return SuccessResponse(
        data=request_data(request, db.get(MentorPersona, request.persona_id)),
        message="커피챗 요청을 수정했습니다.",
    )


@router.delete(
    "/coffee-chat-requests/{request_id}",
    response_model=SuccessResponse[dict[str, object]],
)
def cancel_coffee_chat_request(
    request_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, object]]:
    request = get_owned_request(db, request_id, current_user.id)
    if request.status != CoffeeChatStatus.REQUESTED:
        raise DomainError(
            "COFFEE_CHAT_NOT_CANCELLABLE",
            "수락되거나 종료된 커피챗 요청은 취소할 수 없습니다.",
            409,
        )
    request.status = CoffeeChatStatus.CANCELLED
    request.cancelled_at = datetime.now(UTC)
    db.commit()
    db.refresh(request)
    return SuccessResponse(
        data=request_data(request, db.get(MentorPersona, request.persona_id)),
        message="커피챗 요청을 취소했습니다.",
    )
