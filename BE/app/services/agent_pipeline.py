from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import DomainError
from app.db.session import SessionLocal
from app.models.answer import (
    Answer,
    AnswerAsset,
    AnswerAssetEmbedding,
    Feedback,
)
from app.models.consultation import (
    ConsultationAgentContext,
    ConsultationSession,
    PersonaRecommendation,
)
from app.models.enums import AnswerRoute, AnswerType, ConsultationStatus, JobStatus
from app.models.job import AsyncJob
from app.models.persona import MentorPersona
from app.models.qna import QnaPost
from app.services.mentoring_agent_adapter import build_agent_adapter

RETRYABLE_JOB_TYPES = {
    "consultation_analysis",
    "persona_answer_generation",
    "answer_assetization",
}


class AgentPipeline:
    """웹 작업 상태를 관리하며 실제 판단은 기존 M2M Agent에 위임한다."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.agent = build_agent_adapter(settings)

    def process_analysis_job(self, job_id: str) -> None:
        with SessionLocal() as db:
            job = db.get(AsyncJob, job_id)
            if job is None or job.status != JobStatus.QUEUED:
                return
            session = db.get(ConsultationSession, job.session_id)
            if session is None:
                self._fail_job(db, job, "CONSULTATION_NOT_FOUND", "상담이 없습니다.")
                return
            context = db.get(ConsultationAgentContext, session.id)
            if context is None:
                self._fail_job(db, job, "AGENT_CONTEXT_NOT_FOUND", "Agent 맥락이 없습니다.")
                return

            job.status = JobStatus.PROCESSING
            job.progress = 20
            job.current_step = "agent2_search_and_route"
            db.commit()

            try:
                context_data = self._context_data(session, context)
                core_session_id = self.agent.ensure_core_session(
                    mentee_id=session.mentee_id,
                    core_session_id=context.agent1_raw_output.get("coreSessionId"),
                    refined_question=session.refined_question or session.title,
                    conversation_summary=session.conversation_summary or "",
                    context=context_data,
                )
                context.agent1_raw_output = {
                    **context.agent1_raw_output,
                    "coreSessionId": core_session_id,
                }
                result = self.agent.route(
                    core_session_id=core_session_id,
                    refined_question=session.refined_question or session.title,
                    context=context_data,
                )
                verdict = result.get("verdict", "mentor_needed")
                session.route = verdict
                session.route_reason = (
                    result.get("fallback_reason")
                    or result.get("reason")
                    or result.get("strategy")
                )
                context.agent2_raw_output = result

                if verdict in {"llm_direct", "partial_with_mentor_suggest"}:
                    db.add(
                        Answer(
                            session_id=session.id,
                            answer_type=AnswerType.GENERAL_AI,
                            route=verdict,
                            raw_content=result.get("answer") or "",
                            final_content=result.get("answer") or "",
                            summary=None,
                            confidence_score=result.get("avg_score"),
                            prompt_version="m2m-agent2",
                            model=self.settings.openai_chat_model,
                            source_ids=(
                                result.get("source_trace", {}).get(
                                    "used_answer_ids", []
                                )
                            ),
                        )
                    )

                if verdict == "llm_direct":
                    session.status = ConsultationStatus.AI_ANSWERED
                else:
                    job.progress = 65
                    job.current_step = "agent3_mentor_matching"
                    db.commit()
                    match_result = self.agent.recommend_mentors(
                        core_session_id=core_session_id,
                        refined_question=session.refined_question or session.title,
                        context=context_data,
                        agent2_result=result,
                    )
                    self._store_recommendations(db, session, match_result)
                    session.status = ConsultationStatus.PERSONA_RECOMMENDED

                job.status = JobStatus.COMPLETED
                job.progress = 100
                job.current_step = "completed"
                db.commit()
            except DomainError as exc:
                session.status = ConsultationStatus.FAILED
                self._fail_job(db, job, exc.code, exc.message)
            except Exception as exc:  # noqa: BLE001
                session.status = ConsultationStatus.FAILED
                self._fail_job(db, job, "INTERNAL_ERROR", str(exc))

    def process_persona_answer_job(self, job_id: str) -> None:
        with SessionLocal() as db:
            job = db.get(AsyncJob, job_id)
            if job is None or job.status != JobStatus.QUEUED:
                return
            session = db.get(ConsultationSession, job.session_id)
            if session is None or not session.selected_persona_id:
                self._fail_job(db, job, "PERSONA_NOT_FOUND", "선택한 페르소나가 없습니다.")
                return
            persona = db.get(MentorPersona, session.selected_persona_id)
            context = db.get(ConsultationAgentContext, session.id)
            if persona is None:
                self._fail_job(db, job, "PERSONA_NOT_FOUND", "페르소나를 찾을 수 없습니다.")
                return
            recommendation = db.scalar(
                select(PersonaRecommendation).where(
                    PersonaRecommendation.session_id == session.id,
                    PersonaRecommendation.persona_id == persona.id,
                )
            )

            job.status = JobStatus.PROCESSING
            job.progress = 30
            job.current_step = "persona_answer_generation"
            db.commit()
            try:
                context_data = self._context_data(session, context)
                hard_cases = context_data.get("hard_case_flags", {})
                routing_hints = context_data.get("routing_hints", {})
                result = self.agent.generate_persona_answer(
                    mentor_id=persona.id,
                    refined_question=session.refined_question or session.title,
                    safe_context=context_data.get("safe_context", ""),
                    current_bottleneck=session.current_bottleneck or "",
                    expected_answer_type=session.expected_answer_type or "",
                    bridge_hypothesis=(
                        hard_cases.get("bridge_hypothesis")
                        or routing_hints.get("bridge_hypothesis", "")
                    ),
                    transferable_skills=(
                        hard_cases.get("transferable_skills")
                        or routing_hints.get("transferable_skills", [])
                    ),
                    question_units=context_data.get("question_units", []),
                    recommendation_reason=(
                        recommendation.recommendation_reason
                        if recommendation is not None
                        else ""
                    ),
                )
                db.add(
                    Answer(
                        session_id=session.id,
                        answer_type=AnswerType.PERSONA_AI,
                        route=AnswerRoute.MENTOR_NEEDED,
                        persona_id=persona.id,
                        persona_version=persona.version,
                        raw_content=result["content"],
                        final_content=result["content"],
                        summary=result.get("summary"),
                        prompt_version="m2m-mentor-persona-agent",
                        model=result.get("model", self.settings.openai_chat_model),
                        source_ids=[],
                    )
                )
                session.status = ConsultationStatus.PERSONA_ANSWERED
                job.status = JobStatus.COMPLETED
                job.progress = 100
                job.current_step = "completed"
                db.commit()
            except DomainError as exc:
                session.status = ConsultationStatus.FAILED
                self._fail_job(db, job, exc.code, exc.message)
            except Exception as exc:  # noqa: BLE001
                session.status = ConsultationStatus.FAILED
                self._fail_job(
                    db,
                    job,
                    "PERSONA_ANSWER_GENERATION_FAILED",
                    str(exc),
                )

    def process_assetization_job(self, job_id: str) -> None:
        with SessionLocal() as db:
            job = db.get(AsyncJob, job_id)
            if job is None or job.status != JobStatus.QUEUED:
                return
            session = db.get(ConsultationSession, job.session_id)
            answer = db.scalar(
                select(Answer)
                .where(Answer.session_id == job.session_id)
                .order_by(Answer.created_at.desc())
            )
            if session is None or answer is None:
                self._fail_job(db, job, "ANSWER_NOT_FOUND", "답변을 찾을 수 없습니다.")
                return
            context = db.get(ConsultationAgentContext, session.id)
            feedback = db.scalar(select(Feedback).where(Feedback.answer_id == answer.id))

            job.status = JobStatus.PROCESSING
            job.progress = 30
            job.current_step = "agent4_assetization"
            db.commit()
            try:
                context_data = self._context_data(session, context)
                core_session_id = (
                    context.agent1_raw_output.get("coreSessionId")
                    if context
                    else session.id
                )
                rating = feedback.rating if feedback is not None else None
                satisfaction = (rating - 1) / 4 if rating is not None else None
                taxonomy = context_data.get("taxonomy_tags", {})
                routing = context_data.get("routing_hints", {})
                hard_cases = context_data.get("hard_case_flags", {})
                domain_tags = taxonomy.get("domain_tags", [])
                if not isinstance(domain_tags, list):
                    domain_tags = [str(domain_tags)] if domain_tags else []

                result = self.agent.assetize(
                    session_id=core_session_id,
                    mentor_id=answer.persona_id or "agent2",
                    question_content=session.refined_question or session.title,
                    answer_content=answer.final_content,
                    answer_summarize=answer.summary or answer.final_content[:100],
                    domain_tags=domain_tags,
                    mentor_consent=True,
                    mentee_consent=True,
                    satisfaction_score=satisfaction,
                    taxonomy_tags=taxonomy,
                    source_role=hard_cases.get("source_role", ""),
                    target_role=routing.get("target_role", ""),
                    current_bottleneck=session.current_bottleneck or "",
                    expected_answer_type=session.expected_answer_type or "",
                    question_units=context_data.get("question_units", []),
                )
                self._mirror_asset_result(db, session, answer, result)
                if result.get("is_assetized"):
                    self._create_qna_post(db, session, result)
                session.status = (
                    ConsultationStatus.ASSETIZED
                    if result.get("is_assetized")
                    else ConsultationStatus.COMPLETED
                )
                job.status = JobStatus.COMPLETED
                job.progress = 100
                job.current_step = "completed"
                db.commit()
            except DomainError as exc:
                session.status = ConsultationStatus.FAILED
                self._fail_job(db, job, exc.code, exc.message)
            except Exception as exc:  # noqa: BLE001
                session.status = ConsultationStatus.FAILED
                self._fail_job(db, job, "AGENT4_EXECUTION_FAILED", str(exc))

    def _store_recommendations(
        self,
        db: Session,
        session: ConsultationSession,
        match_result: dict,
    ) -> None:
        top3 = match_result.get("top3", [])
        if not top3:
            raise DomainError(
                "PERSONA_RECOMMENDATION_EMPTY",
                "기존 Agent가 적합한 멘토 페르소나를 찾지 못했습니다.",
                503,
            )
        db.execute(
            delete(PersonaRecommendation).where(
                PersonaRecommendation.session_id == session.id
            )
        )
        for item in top3:
            mentor_id = item["mentor_id"]
            mentor_data = self.agent.get_mentor(mentor_id)
            if mentor_data is None:
                continue
            persona = db.get(MentorPersona, mentor_id)
            mapped = self._persona_values(mentor_data)
            if persona is None:
                persona = MentorPersona(id=mentor_id, **mapped)
                db.add(persona)
            else:
                for field, value in mapped.items():
                    setattr(persona, field, value)
            db.flush()
            db.add(
                PersonaRecommendation(
                    session_id=session.id,
                    persona_id=mentor_id,
                    rank=int(item.get("rank", 0)),
                    match_score=float(item.get("algorithm_score", 0.0)),
                    recommendation_reason=item.get(
                        "recommendation_reason", "기존 Agent 3가 추천했습니다."
                    ),
                    persona_version=persona.version,
                )
            )

    @staticmethod
    def _persona_values(mentor: dict) -> dict:
        info = mentor.get("mentor_info", {})
        background = mentor.get("background", {})
        expertise = mentor.get("domain_tags", [])
        if not isinstance(expertise, list):
            expertise = [str(expertise)] if expertise else []
        return {
            "display_name": info.get("name", "AI 멘토"),
            "current_role": mentor.get("current_role", ""),
            "years_of_experience": int(mentor.get("years_of_experience", 0)),
            "career_history": [background] if background else [],
            "expertise": expertise,
            "profile_summary": mentor.get("matching_summary_text", ""),
            "answer_style": {"isAiPersona": True},
            "matching_summary": mentor.get("be_go")
            or mentor.get("matching_summary_text", ""),
            "system_prompt": "",
            "version": "core-json-v1",
            "active": bool(mentor.get("active", True)),
        }

    @staticmethod
    def _context_data(
        session: ConsultationSession,
        context: ConsultationAgentContext | None,
    ) -> dict:
        if context is None:
            return {
                "conversation_summary": session.conversation_summary or "",
                "current_bottleneck": session.current_bottleneck or "",
                "expected_answer_type": session.expected_answer_type or "",
            }
        return {
            "conversation_summary": session.conversation_summary or "",
            "safe_context": context.safe_context,
            "search_query": context.search_query,
            "match_query": context.match_query,
            "current_bottleneck": session.current_bottleneck or "",
            "expected_answer_type": session.expected_answer_type or "",
            "question_units": context.question_units,
            "taxonomy_tags": context.taxonomy_tags,
            "routing_hints": context.routing_hints,
            "hard_case_flags": context.hard_case_flags,
        }

    @staticmethod
    def _mirror_asset_result(
        db: Session,
        session: ConsultationSession,
        answer: Answer,
        result: dict,
    ) -> None:
        reject = result.get("reject_reasons", {})
        active = bool(result.get("is_assetized"))
        privacy_failed = (
            reject.get("personal_context") == "isolated"
            or reject.get("company_sensitivity") == "sensitive"
        )
        quality_failed = (
            reject.get("length") is False
            or reject.get("info_density") == "low"
            or reject.get("recency") == "stale"
        )
        asset = db.scalar(
            select(AnswerAsset).where(AnswerAsset.answer_id == answer.id)
        )
        if asset is None:
            asset = AnswerAsset(
                answer_id=answer.id,
                session_id=session.id,
                anonymized_question=result.get("question_content", ""),
                anonymized_answer=result.get("answer_content", ""),
                privacy_check_status="pending",
                quality_check_status="pending",
                active=False,
            )
            db.add(asset)
        asset.anonymized_question = result.get("question_content", "")
        asset.anonymized_answer = result.get("answer_content", "")
        asset.privacy_check_status = "failed" if privacy_failed else "passed"
        asset.quality_check_status = "failed" if quality_failed else "passed"
        asset.active = active
        asset.deleted_at = None
        asset.embedding_id = result.get("answer_id") if active else None

        vector = result.get("embedding")
        if active and isinstance(vector, list) and vector:
            db.flush()
            embedding = db.get(AnswerAssetEmbedding, asset.id)
            if embedding is None:
                db.add(
                    AnswerAssetEmbedding(
                        asset_id=asset.id,
                        vector=vector,
                        model="text-embedding-3-small",
                    )
                )
            else:
                embedding.vector = vector
                embedding.model = "text-embedding-3-small"

    @staticmethod
    def _create_qna_post(db: Session, session: ConsultationSession, result: dict) -> None:
        """동의 후 자산화에 성공한 답변을 Q&A 게시판에도 익명으로 게재한다."""
        domain_tags = result.get("domain_tags") or []
        category = str(domain_tags[0]) if domain_tags else "진로상담"
        question = result.get("question_content") or session.title
        answer_content = result.get("answer_content", "")
        db.add(
            QnaPost(
                author_id=session.mentee_id,
                category=category[:50],
                title=question[:120],
                content=f"Q. {question}\n\nA. {answer_content}",
                anonymous=True,
            )
        )

    @staticmethod
    def _fail_job(
        db: Session,
        job: AsyncJob,
        code: str,
        message: str,
    ) -> None:
        job.status = JobStatus.FAILED
        job.current_step = "failed"
        job.error = {
            "code": code,
            "message": message,
            "retryable": job.job_type in RETRYABLE_JOB_TYPES,
        }
        db.commit()
