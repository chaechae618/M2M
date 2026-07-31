from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.core.exceptions import DomainError
from app.models.answer import (
    Answer,
    AnswerAsset,
    AnswerAssetEmbedding,
    Feedback,
    ReuseConsent,
)
from app.models.enums import ConsultationStatus, JobStatus
from app.models.job import AsyncJob
from app.schemas.common import SuccessResponse
from app.schemas.feedback import FeedbackCreateRequest, ReuseConsentRequest
from app.services.agent_pipeline import AgentPipeline
from app.services.consultation_service import ConsultationService
from app.services.mentoring_agent_adapter import build_agent_adapter

router = APIRouter(prefix="/consultations", tags=["Feedback and Assets"])


def get_owned_answer(
    db: DbSession,
    session_id: str,
    answer_id: str,
) -> Answer:
    answer = db.scalar(
        select(Answer).where(
            Answer.id == answer_id,
            Answer.session_id == session_id,
        )
    )
    if answer is None:
        raise DomainError("ANSWER_NOT_FOUND", "답변을 찾을 수 없습니다.", 404)
    return answer


@router.post(
    "/{session_id}/feedback",
    response_model=SuccessResponse[dict[str, object]],
    status_code=status.HTTP_201_CREATED,
)
def create_feedback(
    session_id: str,
    payload: FeedbackCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    session = ConsultationService(db, current_user, settings).get_owned(session_id)
    answer = get_owned_answer(db, session.id, payload.answer_id)
    existing = db.scalar(select(Feedback).where(Feedback.answer_id == answer.id))
    if existing is not None:
        raise DomainError(
            "FEEDBACK_ALREADY_SUBMITTED",
            "이미 만족도 평가를 제출했습니다.",
            409,
        )
    feedback = Feedback(
        answer_id=answer.id,
        mentee_id=current_user.id,
        rating=payload.rating,
        helpful_tags=payload.helpful_tags,
        comment=payload.comment,
    )
    db.add(feedback)
    session.status = ConsultationStatus.AWAITING_FEEDBACK
    db.commit()
    db.refresh(feedback)
    return SuccessResponse(
        data={
            "feedbackId": feedback.id,
            "answerId": answer.id,
            "rating": feedback.rating,
            "route": answer.route,
            "answerType": answer.answer_type,
            "personaId": answer.persona_id,
            "personaVersion": answer.persona_version,
            "createdAt": feedback.created_at,
        }
    )


@router.put(
    "/{session_id}/reuse-consent",
    response_model=SuccessResponse[dict[str, object]],
)
def set_reuse_consent(
    session_id: str,
    payload: ReuseConsentRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    session = ConsultationService(db, current_user, settings).get_owned(session_id)
    answer = get_owned_answer(db, session.id, payload.answer_id)
    consent = db.scalar(
        select(ReuseConsent).where(ReuseConsent.answer_id == answer.id)
    )
    now = datetime.now(UTC)
    if consent is None:
        consent = ReuseConsent(
            answer_id=answer.id,
            mentee_id=current_user.id,
            consent=payload.consent,
            scope=payload.scope,
        )
        db.add(consent)
    consent.consent = payload.consent
    consent.scope = payload.scope

    if not payload.consent:
        consent.withdrawn_at = now
        asset = db.scalar(
            select(AnswerAsset).where(AnswerAsset.answer_id == answer.id)
        )
        if asset is not None:
            core_answer_id = asset.embedding_id
            if core_answer_id:
                build_agent_adapter(settings).withdraw_asset(core_answer_id)
            embedding = db.get(AnswerAssetEmbedding, asset.id)
            if embedding is not None:
                db.delete(embedding)
            asset.active = False
            asset.embedding_id = None
            asset.deleted_at = now
        session.status = ConsultationStatus.COMPLETED
        db.commit()
        return SuccessResponse(
            data={
                "consent": False,
                "retrievalExcluded": True,
                "assetDeleted": asset is not None,
                "embeddingDeleted": asset is not None,
                "consultationHistoryRetained": True,
            }
        )

    consent.consented_at = now
    consent.withdrawn_at = None
    session.status = ConsultationStatus.ASSETIZING
    job = AsyncJob(
        owner_id=current_user.id,
        session_id=session.id,
        job_type="answer_assetization",
        status=JobStatus.QUEUED,
        progress=0,
        current_step="waiting_for_assetization",
        result_url=f"/api/v1/consultations/{session.id}/assetization",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(AgentPipeline(settings).process_assetization_job, job.id)
    response = SuccessResponse(
        data={
            "consent": True,
            "sessionStatus": ConsultationStatus.ASSETIZING,
            "jobId": job.id,
            "pollingUrl": f"/api/v1/jobs/{job.id}",
        }
    )
    return response


@router.get(
    "/{session_id}/assetization",
    response_model=SuccessResponse[dict[str, object]],
)
def get_assetization(
    session_id: str,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    session = ConsultationService(db, current_user, settings).get_owned(session_id)
    asset = db.scalar(
        select(AnswerAsset)
        .where(AnswerAsset.session_id == session.id)
        .order_by(AnswerAsset.created_at.desc())
    )
    if asset is None:
        return SuccessResponse(
            data={
                "status": session.status,
                "assetId": None,
                "privacyCheck": "pending",
                "qualityCheck": "pending",
                "embeddingStored": False,
            }
        )
    return SuccessResponse(
        data={
            "status": session.status,
            "assetId": asset.id,
            "privacyCheck": asset.privacy_check_status,
            "qualityCheck": asset.quality_check_status,
            "embeddingStored": bool(asset.embedding_id),
            "active": asset.active,
            "assetizedAt": asset.updated_at,
        }
    )
