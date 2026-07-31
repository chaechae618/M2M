from fastapi import APIRouter, BackgroundTasks, status
from sqlalchemy import delete, select

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.core.exceptions import DomainError
from app.models.answer import Answer
from app.models.consultation import ConsultationSession, PersonaRecommendation
from app.models.enums import ConsultationStatus, JobStatus
from app.models.job import AsyncJob
from app.schemas.common import SuccessResponse
from app.services.agent_pipeline import RETRYABLE_JOB_TYPES, AgentPipeline

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}", response_model=SuccessResponse[dict[str, object]])
def get_job(
    job_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[dict[str, object]]:
    job = db.scalar(
        select(AsyncJob).where(
            AsyncJob.id == job_id,
            AsyncJob.owner_id == current_user.id,
        )
    )
    if job is None:
        raise DomainError("JOB_NOT_FOUND", "작업을 찾을 수 없습니다.", 404)
    return SuccessResponse(
        data={
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
    )


@router.post(
    "/{job_id}/retry",
    response_model=SuccessResponse[dict[str, object]],
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    job = db.scalar(
        select(AsyncJob).where(
            AsyncJob.id == job_id,
            AsyncJob.owner_id == current_user.id,
        )
    )
    if job is None:
        raise DomainError("JOB_NOT_FOUND", "작업을 찾을 수 없습니다.", 404)
    if job.status != JobStatus.FAILED:
        raise DomainError(
            "JOB_NOT_FAILED",
            "실패한 작업만 재시도할 수 있습니다.",
            409,
        )
    if job.job_type not in RETRYABLE_JOB_TYPES:
        raise DomainError(
            "JOB_NOT_RETRYABLE",
            "재시도를 지원하지 않는 작업입니다.",
            409,
        )

    session = db.get(ConsultationSession, job.session_id)
    if session is None:
        raise DomainError(
            "RETRY_PREREQUISITE_MISSING",
            "재시도할 상담을 찾을 수 없습니다.",
            409,
        )

    pipeline = AgentPipeline(settings)
    if job.job_type == "consultation_analysis":
        db.execute(
            delete(Answer).where(
                Answer.session_id == session.id,
                Answer.answer_type == "general_ai",
            )
        )
        db.execute(
            delete(PersonaRecommendation).where(
                PersonaRecommendation.session_id == session.id
            )
        )
        session.route = None
        session.route_reason = None
        session.status = ConsultationStatus.ANALYZING
        current_step = "waiting_for_agent2"
        processor = pipeline.process_analysis_job
    elif job.job_type == "persona_answer_generation":
        if not session.selected_persona_id:
            raise DomainError(
                "RETRY_PREREQUISITE_MISSING",
                "선택된 페르소나가 없어 답변 생성을 재시도할 수 없습니다.",
                409,
            )
        session.status = ConsultationStatus.PERSONA_ANSWER_GENERATING
        current_step = "waiting_for_persona"
        processor = pipeline.process_persona_answer_job
    else:
        answer_exists = db.scalar(
            select(Answer.id).where(Answer.session_id == session.id)
        )
        if answer_exists is None:
            raise DomainError(
                "RETRY_PREREQUISITE_MISSING",
                "자산화할 답변이 없어 재시도할 수 없습니다.",
                409,
            )
        session.status = ConsultationStatus.ASSETIZING
        current_step = "waiting_for_assetization"
        processor = pipeline.process_assetization_job

    job.status = JobStatus.QUEUED
    job.progress = 0
    job.current_step = current_step
    job.error = None
    db.commit()
    background_tasks.add_task(processor, job.id)
    return SuccessResponse(
        data={
            "jobId": job.id,
            "jobType": job.job_type,
            "status": JobStatus.QUEUED,
            "progress": 0,
            "currentStep": current_step,
            "pollingUrl": f"/api/v1/jobs/{job.id}",
        },
        message="실패한 작업을 다시 시작했습니다.",
    )
