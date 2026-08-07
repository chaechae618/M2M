from math import ceil

from fastapi import APIRouter, BackgroundTasks, Header, Query, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.models.answer import Answer, Feedback, ReuseConsent
from app.models.consultation import ConsultationMessage, ConsultationSession
from app.models.job import AsyncJob
from app.schemas.common import SuccessResponse
from app.schemas.consultation import (
    ConsultationCreateRequest,
    ConsultationMessageRequest,
    RefinedQuestionRegenerateRequest,
    RefinedQuestionUpdateRequest,
)
from app.services.agent_pipeline import AgentPipeline
from app.services.consultation_service import ConsultationService

router = APIRouter(prefix="/consultations", tags=["Consultations"])


def revision_data(session: ConsultationSession) -> dict[str, object]:
    used = session.refined_question_revision_count
    editable = session.status == "awaiting_confirmation"
    return {
        "used": used,
        "limit": 3,
        "remaining": max(0, 3 - used),
        "canRegenerate": editable and used < 3,
        "canEditDirectly": editable,
    }


def session_summary(session: ConsultationSession) -> dict[str, object]:
    return {
        "id": session.id,
        "title": session.title,
        "status": session.status,
        "refinedQuestion": session.refined_question,
        "refinedQuestionRevision": revision_data(session),
        "route": session.route,
        "createdAt": session.created_at,
        "updatedAt": session.updated_at,
    }


def message_data(message: ConsultationMessage) -> dict[str, object]:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "createdAt": message.created_at,
    }


def refined_question_data(session: ConsultationSession) -> dict[str, object]:
    return {
        "content": session.refined_question,
        "conversationSummary": session.conversation_summary,
        "currentBottleneck": session.current_bottleneck,
        "expectedAnswerType": session.expected_answer_type,
    }


def answer_source_data(answer: Answer) -> dict[str, object] | None:
    """llm_direct 계열 답변이 사용한 RAG JSON 자산을 응답에 표시한다."""
    if answer.route not in {"llm_direct", "partial_with_mentor_suggest"}:
        return None

    answer_ids = answer.source_ids or []
    used_rag_assets = bool(answer_ids)
    return {
        "mode": "rag_json_db" if used_rag_assets else "llm_general_knowledge",
        "jsonDatabase": "mentor_answers.json" if used_rag_assets else None,
        "answerIds": answer_ids,
    }


def answer_data(answer: Answer | None) -> dict[str, object] | None:
    if answer is None:
        return None
    return {
        "id": answer.id,
        "answerType": answer.answer_type,
        "route": answer.route,
        "content": answer.final_content,
        "summary": answer.summary,
        "confidenceScore": answer.confidence_score,
        "model": answer.model,
        "promptVersion": answer.prompt_version,
        "source": answer_source_data(answer),
        "persona": (
            {
                "personaId": answer.persona_id,
                "personaVersion": answer.persona_version,
                "isAiPersona": True,
            }
            if answer.persona_id
            else None
        ),
        "generatedAt": answer.created_at,
    }


def job_data(job: AsyncJob | None) -> dict[str, object] | None:
    if job is None:
        return None
    return {
        "jobId": job.id,
        "jobType": job.job_type,
        "status": job.status,
        "progress": job.progress,
        "currentStep": job.current_step,
        "resultUrl": job.result_url,
        "error": job.error,
        "createdAt": job.created_at,
        "updatedAt": job.updated_at,
    }


def feedback_data(feedback: Feedback | None) -> dict[str, object] | None:
    if feedback is None:
        return None
    return {
        "id": feedback.id,
        "answerId": feedback.answer_id,
        "rating": feedback.rating,
        "createdAt": feedback.created_at,
    }


def consent_data(consent: ReuseConsent | None) -> dict[str, object] | None:
    if consent is None:
        return None
    return {
        "id": consent.id,
        "answerId": consent.answer_id,
        "consent": consent.consent,
        "scope": consent.scope,
        "createdAt": consent.created_at,
        "updatedAt": consent.updated_at,
    }


@router.post(
    "",
    response_model=SuccessResponse[dict[str, object]],
    status_code=status.HTTP_201_CREATED,
)
def create_consultation(
    payload: ConsultationCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    session, assistant = ConsultationService(db, current_user, settings).create(
        payload.initial_message
    )
    return SuccessResponse(
        data={
            "session": session_summary(session),
            "assistantMessage": message_data(assistant),
        }
    )


@router.get("", response_model=SuccessResponse[dict[str, object]])
def list_consultations(
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    consultation_status: str | None = Query(default=None, alias="status"),
    route: str | None = None,
    query: str | None = Query(default=None, max_length=200),
) -> SuccessResponse[dict[str, object]]:
    sessions, total = ConsultationService(db, current_user, settings).list(
        page,
        limit,
        consultation_status,
        route,
        query,
    )
    total_pages = ceil(total / limit) if total else 0
    return SuccessResponse(
        data={
            "items": [session_summary(item) for item in sessions],
            "pagination": {
                "currentPage": page,
                "totalPages": total_pages,
                "totalItems": total,
                "hasNext": page < total_pages,
                "hasPrev": page > 1,
            },
        }
    )


@router.get("/{session_id}", response_model=SuccessResponse[dict[str, object]])
def get_consultation(
    session_id: str,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    service = ConsultationService(db, current_user, settings)
    session = service.get_owned(session_id)
    latest_job = db.scalar(
        select(AsyncJob)
        .where(AsyncJob.session_id == session.id, AsyncJob.owner_id == current_user.id)
        .order_by(AsyncJob.updated_at.desc())
    )
    answer = db.scalar(
        select(Answer)
        .where(Answer.session_id == session.id)
        .order_by(Answer.created_at.desc())
    )
    feedback = (
        db.scalar(select(Feedback).where(Feedback.answer_id == answer.id))
        if answer is not None
        else None
    )
    consent = (
        db.scalar(select(ReuseConsent).where(ReuseConsent.answer_id == answer.id))
        if answer is not None
        else None
    )
    return SuccessResponse(
        data={
            "session": session_summary(session),
            "messages": [message_data(item) for item in service.messages(session.id)],
            "refinedQuestion": (
                refined_question_data(session) if session.refined_question else None
            ),
            "latestJob": job_data(latest_job),
            "answer": answer_data(answer),
            "feedback": feedback_data(feedback),
            "reuseConsent": consent_data(consent),
        }
    )


@router.post(
    "/{session_id}/messages",
    response_model=SuccessResponse[dict[str, object]],
)
def add_message(
    session_id: str,
    payload: ConsultationMessageRequest,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    session, assistant = ConsultationService(db, current_user, settings).add_message(
        session_id,
        payload.content,
    )
    return SuccessResponse(
        data={
            "sessionStatus": session.status,
            "needMoreInfo": session.status == "collecting_context",
            "assistantMessage": message_data(assistant) if assistant else None,
            "refinedQuestion": refined_question_data(session),
            "refinedQuestionRevision": revision_data(session),
        }
    )


@router.post(
    "/{session_id}/refined-question/regenerate",
    response_model=SuccessResponse[dict[str, object]],
)
def regenerate_refined_question(
    session_id: str,
    payload: RefinedQuestionRegenerateRequest,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    session = ConsultationService(db, current_user, settings).regenerate_refined_question(
        session_id,
        payload.instruction,
    )
    return SuccessResponse(
        data={
            "refinedQuestion": refined_question_data(session),
            "refinedQuestionRevision": revision_data(session),
        }
    )


@router.patch(
    "/{session_id}/refined-question",
    response_model=SuccessResponse[dict[str, object]],
)
def update_refined_question(
    session_id: str,
    payload: RefinedQuestionUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    session = ConsultationService(db, current_user, settings).update_refined_question(
        session_id,
        payload.content,
    )
    return SuccessResponse(
        data={
            "refinedQuestion": refined_question_data(session),
            "refinedQuestionRevision": revision_data(session),
        }
    )


@router.post(
    "/{session_id}/confirm",
    response_model=SuccessResponse[dict[str, object]],
    status_code=status.HTTP_202_ACCEPTED,
)
def confirm_refined_question(
    session_id: str,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> SuccessResponse[dict[str, object]]:
    # 키 저장 및 중복 요청 재사용은 Agent 2 작업 실행 단계에서 확장한다.
    _ = idempotency_key
    session, job = ConsultationService(db, current_user, settings).confirm(session_id)
    background_tasks.add_task(AgentPipeline(settings).process_analysis_job, job.id)
    return SuccessResponse(
        data={
            "sessionId": session.id,
            "sessionStatus": session.status,
            "jobId": job.id,
            "jobStatus": job.status,
            "pollingUrl": f"/api/v1/jobs/{job.id}",
        }
    )


@router.get(
    "/{session_id}/result",
    response_model=SuccessResponse[dict[str, object]],
)
def get_consultation_result(
    session_id: str,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    session = ConsultationService(db, current_user, settings).get_owned(session_id)
    answer = db.scalar(
        select(Answer)
        .where(Answer.session_id == session.id)
        .order_by(Answer.created_at.desc())
    )
    return SuccessResponse(
        data={
            "sessionId": session.id,
            "status": session.status,
            "route": session.route,
            "reason": session.route_reason,
            "answer": answer_data(answer),
        }
    )


@router.post(
    "/{session_id}/complete",
    response_model=SuccessResponse[dict[str, object]],
)
def complete_consultation(
    session_id: str,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    session = ConsultationService(db, current_user, settings).complete(session_id)
    return SuccessResponse(
        data={
            "sessionId": session.id,
            "status": session.status,
            "completedAt": session.completed_at,
        },
        message="상담을 완료했습니다.",
    )


@router.delete(
    "/{session_id}",
    response_model=SuccessResponse[dict[str, object]],
)
def cancel_consultation(
    session_id: str,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    session = ConsultationService(db, current_user, settings).cancel(session_id)
    return SuccessResponse(
        data={"sessionId": session.id, "status": session.status},
        message="상담을 취소했습니다.",
    )
