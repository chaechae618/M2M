from fastapi import APIRouter, BackgroundTasks, Header, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.core.exceptions import DomainError
from app.models.consultation import PersonaRecommendation
from app.models.enums import ConsultationStatus, JobStatus
from app.models.job import AsyncJob
from app.models.persona import MentorPersona
from app.schemas.common import SuccessResponse
from app.schemas.consultation import PersonaSelectionRequest
from app.services.agent_pipeline import AgentPipeline
from app.services.consultation_service import ConsultationService

router = APIRouter(prefix="/consultations", tags=["Persona Mentors"])


@router.get(
    "/{session_id}/persona-recommendations",
    response_model=SuccessResponse[dict[str, object]],
)
def get_persona_recommendations(
    session_id: str,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    session = ConsultationService(db, current_user, settings).get_owned(session_id)
    if session.status not in {
        ConsultationStatus.PERSONA_RECOMMENDED,
        ConsultationStatus.PERSONA_ANSWER_GENERATING,
        ConsultationStatus.PERSONA_ANSWERED,
    }:
        raise DomainError(
            "PERSONA_RECOMMENDATION_NOT_READY",
            "페르소나 추천이 아직 준비되지 않았습니다.",
            409,
        )
    rows = db.execute(
        select(PersonaRecommendation, MentorPersona)
        .join(MentorPersona, MentorPersona.id == PersonaRecommendation.persona_id)
        .where(PersonaRecommendation.session_id == session.id)
        .order_by(PersonaRecommendation.rank)
    ).all()
    return SuccessResponse(
        data={
            "sessionId": session.id,
            "personas": [
                {
                    "rank": recommendation.rank,
                    "personaId": persona.id,
                    "displayName": persona.display_name,
                    "currentRole": persona.current_role,
                    "yearsOfExperience": persona.years_of_experience,
                    "expertise": persona.expertise,
                    "profileSummary": persona.profile_summary,
                    "recommendationReason": recommendation.recommendation_reason,
                    "matchScore": recommendation.match_score,
                    "personaVersion": recommendation.persona_version,
                    "isAiPersona": True,
                }
                for recommendation, persona in rows
            ],
            "disclaimer": "추천 멘토는 실제 인물이 아닌 AI 페르소나입니다.",
        }
    )


@router.post(
    "/{session_id}/persona-selection",
    response_model=SuccessResponse[dict[str, object]],
    status_code=status.HTTP_202_ACCEPTED,
)
def select_persona(
    session_id: str,
    payload: PersonaSelectionRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> SuccessResponse[dict[str, object]]:
    _ = idempotency_key
    session = ConsultationService(db, current_user, settings).get_owned(session_id)
    if session.status != ConsultationStatus.PERSONA_RECOMMENDED:
        raise DomainError(
            "INVALID_SESSION_STATE",
            "페르소나 추천 완료 상태에서만 선택할 수 있습니다.",
            409,
        )
    recommendation = db.scalar(
        select(PersonaRecommendation).where(
            PersonaRecommendation.session_id == session.id,
            PersonaRecommendation.persona_id == payload.persona_id,
        )
    )
    if recommendation is None:
        raise DomainError(
            "PERSONA_NOT_RECOMMENDED",
            "추천된 Top 3 페르소나만 선택할 수 있습니다.",
            400,
        )
    persona = db.get(MentorPersona, payload.persona_id)
    if persona is None or not persona.active:
        raise DomainError("PERSONA_NOT_FOUND", "페르소나를 찾을 수 없습니다.", 404)

    session.selected_persona_id = persona.id
    session.selected_persona_version = persona.version
    session.status = ConsultationStatus.PERSONA_ANSWER_GENERATING
    job = AsyncJob(
        owner_id=current_user.id,
        session_id=session.id,
        job_type="persona_answer_generation",
        status=JobStatus.QUEUED,
        progress=0,
        current_step="waiting_for_persona",
        result_url=f"/api/v1/consultations/{session.id}/result",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(AgentPipeline(settings).process_persona_answer_job, job.id)
    return SuccessResponse(
        data={
            "sessionId": session.id,
            "selectedPersona": {
                "personaId": persona.id,
                "displayName": persona.display_name,
                "personaVersion": persona.version,
                "isAiPersona": True,
            },
            "sessionStatus": ConsultationStatus.PERSONA_ANSWER_GENERATING,
            "jobId": job.id,
            "pollingUrl": f"/api/v1/jobs/{job.id}",
        }
    )
