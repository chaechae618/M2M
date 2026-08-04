from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import DomainError
from app.models.auth import User
from app.models.consultation import (
    ConsultationAgentContext,
    ConsultationMessage,
    ConsultationSession,
)
from app.models.enums import ConsultationStatus, JobStatus, MessageRole
from app.models.job import AsyncJob
from app.services.mentoring_agent_adapter import (
    CoreMentoringAgentAdapter,
    RefineResult,
    build_agent_adapter,
)

class ConsultationService:
    def __init__(self, db: Session, user: User, settings: Settings | None = None) -> None:
        self.db = db
        self.user = user
        self.agent = build_agent_adapter(settings) if settings is not None else None

    def create(self, initial_message: str) -> tuple[ConsultationSession, ConsultationMessage]:
        title = initial_message.strip().replace("\n", " ")[:60]
        session = ConsultationSession(
            mentee_id=self.user.id,
            title=title,
            status=ConsultationStatus.COLLECTING_CONTEXT,
        )
        self.db.add(session)
        self.db.flush()
        user_message = ConsultationMessage(
            session_id=session.id,
            role=MessageRole.USER,
            content=initial_message.strip(),
        )
        self.db.add(user_message)
        self.db.flush()
        result = self._require_agent().refine(
            [{"role": MessageRole.USER, "content": user_message.content}],
            mentee_id=self.user.id,
        )
        assistant = self._apply_refine_result(session, result)
        if assistant is None:
            assistant = ConsultationMessage(
                session_id=session.id,
                role=MessageRole.ASSISTANT,
                content="정제 질문이 준비되었습니다. 내용을 확인해주세요.",
            )
        self.db.add(assistant)
        self.db.commit()
        self.db.refresh(session)
        self.db.refresh(assistant)
        return session, assistant

    def get_owned(self, session_id: str) -> ConsultationSession:
        session = self.db.scalar(
            select(ConsultationSession).where(
                ConsultationSession.id == session_id,
                ConsultationSession.mentee_id == self.user.id,
            )
        )
        if session is None:
            raise DomainError("CONSULTATION_NOT_FOUND", "상담을 찾을 수 없습니다.", 404)
        return session

    def list(
        self,
        page: int,
        limit: int,
        status: str | None,
        route: str | None,
        query: str | None,
    ) -> tuple[list[ConsultationSession], int]:
        conditions = [ConsultationSession.mentee_id == self.user.id]
        if status:
            conditions.append(ConsultationSession.status == status)
        if route:
            conditions.append(ConsultationSession.route == route)
        if query:
            pattern = f"%{query.strip()}%"
            conditions.append(
                or_(
                    ConsultationSession.title.ilike(pattern),
                    ConsultationSession.refined_question.ilike(pattern),
                )
            )

        total = self.db.scalar(
            select(func.count()).select_from(ConsultationSession).where(*conditions)
        )
        sessions = list(
            self.db.scalars(
                select(ConsultationSession)
                .where(*conditions)
                .order_by(ConsultationSession.updated_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        )
        return sessions, total or 0

    def messages(self, session_id: str) -> list[ConsultationMessage]:
        return list(
            self.db.scalars(
                select(ConsultationMessage)
                .where(ConsultationMessage.session_id == session_id)
                .order_by(ConsultationMessage.created_at.asc())
            )
        )

    def add_message(
        self,
        session_id: str,
        content: str,
    ) -> tuple[ConsultationSession, ConsultationMessage | None]:
        session = self.get_owned(session_id)
        if session.status != ConsultationStatus.COLLECTING_CONTEXT:
            raise DomainError(
                "INVALID_SESSION_STATE",
                "현재 상담 상태에서는 메시지를 추가할 수 없습니다.",
                409,
            )

        user_message = ConsultationMessage(
            session_id=session.id,
            role=MessageRole.USER,
            content=content.strip(),
        )
        self.db.add(user_message)
        self.db.flush()

        history = [
            {"role": item.role, "content": item.content}
            for item in self.messages(session.id)
        ]
        result = self._require_agent().refine(
            history,
            mentee_id=self.user.id,
        )
        assistant = self._apply_refine_result(session, result)
        if assistant is not None:
            self.db.add(assistant)
        self.db.commit()
        self.db.refresh(session)
        if assistant is not None:
            self.db.refresh(assistant)
        return session, assistant

    def regenerate_refined_question(
        self,
        session_id: str,
        instruction: str,
    ) -> ConsultationSession:
        session = self.get_owned(session_id)
        self._require_awaiting_confirmation(session)
        if session.refined_question_revision_count >= 3:
            raise DomainError(
                "REFINED_QUESTION_REVISION_LIMIT_EXCEEDED",
                "정제 질문 재생성은 최대 3회까지 가능합니다.",
                409,
            )

        history = [
            {"role": item.role, "content": item.content}
            for item in self.messages(session.id)
        ]
        history.append(
            {
                "role": MessageRole.ASSISTANT,
                "content": f"현재 정제 질문: {session.refined_question}",
            }
        )
        result = self._require_agent().refine(
            history,
            mentee_id=self.user.id,
            force_finalize=True,
            revision_instruction=instruction,
        )
        if not result.refined_question:
            raise DomainError(
                "AI_SERVICE_UNAVAILABLE",
                "정제 질문을 다시 생성하지 못했습니다.",
                503,
            )
        self._apply_refine_result(session, result)
        session.refined_question_revision_count += 1
        self.db.commit()
        self.db.refresh(session)
        return session

    def update_refined_question(
        self,
        session_id: str,
        content: str,
    ) -> ConsultationSession:
        session = self.get_owned(session_id)
        self._require_awaiting_confirmation(session)
        session.refined_question = content.strip()
        context = self.db.get(ConsultationAgentContext, session.id)
        if context is not None:
            context.search_query = session.refined_question
            context.match_query = session.refined_question
        self.db.commit()
        self.db.refresh(session)
        return session

    def confirm(self, session_id: str) -> tuple[ConsultationSession, AsyncJob]:
        session = self.get_owned(session_id)
        self._require_awaiting_confirmation(session)
        if not session.refined_question:
            raise DomainError(
                "REFINED_QUESTION_NOT_READY",
                "정제 질문이 아직 준비되지 않았습니다.",
                409,
            )

        session.status = ConsultationStatus.ANALYZING
        job = AsyncJob(
            owner_id=self.user.id,
            session_id=session.id,
            job_type="consultation_analysis",
            status=JobStatus.QUEUED,
            progress=0,
            current_step="waiting_for_agent2",
            result_url=f"/api/v1/consultations/{session.id}/result",
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(session)
        self.db.refresh(job)
        return session, job

    def complete(self, session_id: str) -> ConsultationSession:
        session = self.get_owned(session_id)
        if session.status == ConsultationStatus.COMPLETED:
            return session

        completable_statuses = {
            ConsultationStatus.AI_ANSWERED,
            ConsultationStatus.PERSONA_ANSWERED,
            ConsultationStatus.AWAITING_FEEDBACK,
            ConsultationStatus.ASSETIZED,
        }
        if session.status not in completable_statuses:
            raise DomainError(
                "INVALID_SESSION_STATE",
                "답변이 완료된 상담만 완료 처리할 수 있습니다.",
                409,
            )

        session.status = ConsultationStatus.COMPLETED
        session.completed_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(session)
        return session

    def cancel(self, session_id: str) -> ConsultationSession:
        session = self.get_owned(session_id)
        if session.status in {ConsultationStatus.COMPLETED, ConsultationStatus.CANCELLED}:
            raise DomainError(
                "INVALID_SESSION_STATE",
                "이미 완료되거나 취소된 상담입니다.",
                409,
            )
        session.status = ConsultationStatus.CANCELLED
        session.completed_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(session)
        return session

    @staticmethod
    def _require_awaiting_confirmation(session: ConsultationSession) -> None:
        if session.status != ConsultationStatus.AWAITING_CONFIRMATION:
            raise DomainError(
                "INVALID_SESSION_STATE",
                "정제 질문 확인 단계에서만 실행할 수 있습니다.",
                409,
            )

    def _require_agent(self) -> CoreMentoringAgentAdapter:
        if self.agent is None:
            raise RuntimeError("Mentoring Agent adapter requires application settings")
        return self.agent

    def _apply_refine_result(
        self,
        session: ConsultationSession,
        result: RefineResult,
    ) -> ConsultationMessage | None:
        if result.need_more_info:
            session.status = ConsultationStatus.COLLECTING_CONTEXT
            return ConsultationMessage(
                session_id=session.id,
                role=MessageRole.ASSISTANT,
                content=result.assistant_message or "조금 더 구체적으로 알려주세요.",
            )

        if not result.refined_question:
            raise DomainError(
                "AI_SERVICE_UNAVAILABLE",
                "Agent 1이 정제 질문을 생성하지 못했습니다.",
                503,
            )
        session.refined_question = result.refined_question
        session.conversation_summary = result.conversation_summary
        session.current_bottleneck = result.current_bottleneck
        session.expected_answer_type = result.expected_answer_type
        session.status = ConsultationStatus.AWAITING_CONFIRMATION

        context = self.db.get(ConsultationAgentContext, session.id)
        if context is None:
            context = ConsultationAgentContext(session_id=session.id)
            self.db.add(context)
        context.safe_context = result.safe_context
        context.search_query = result.search_query or result.refined_question
        context.match_query = result.match_query or result.refined_question
        context.question_units = result.question_units
        context.taxonomy_tags = result.taxonomy_tags
        context.routing_hints = result.routing_hints
        context.hard_case_flags = result.hard_case_flags
        context.agent1_raw_output = result.raw
        return None
