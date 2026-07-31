"""FastAPI와 M2M-mentoring-agent 사이의 얇은 연결 계층."""

from __future__ import annotations

import importlib
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.exceptions import DomainError

logger = logging.getLogger(__name__)


@dataclass
class RefineResult:
    need_more_info: bool
    assistant_message: str | None = None
    refined_question: str | None = None
    conversation_summary: str = ""
    safe_context: str = ""
    search_query: str = ""
    match_query: str = ""
    current_bottleneck: str = ""
    expected_answer_type: str = ""
    question_units: list[dict] = field(default_factory=list)
    taxonomy_tags: dict = field(default_factory=dict)
    routing_hints: dict = field(default_factory=dict)
    hard_case_flags: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)


class CoreMentoringAgentAdapter:
    """기존 Agent를 호출하고 웹 계층이 쓰기 좋은 형태로만 변환한다."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.agent_root = self._resolve_agent_root(settings.mentoring_agent_root)
        self._configure_environment()

    @staticmethod
    def _resolve_agent_root(configured: Path) -> Path:
        path = configured if configured.is_absolute() else (Path.cwd() / configured)
        path = path.resolve()
        if not (path / "agents").is_dir():
            raise DomainError(
                "MENTORING_AGENT_NOT_FOUND",
                f"M2M-mentoring-agent 폴더를 찾을 수 없습니다: {path}",
                503,
            )
        return path

    def _configure_environment(self) -> None:
        root = str(self.agent_root)
        if root not in sys.path:
            sys.path.insert(0, root)
        if self.settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.settings.openai_api_key
        os.environ["AGENT2_OPENAI_MODEL"] = self.settings.openai_chat_model
        os.environ["MENTOR_ANSWER_OPENAI_MODEL"] = self.settings.openai_chat_model

    @staticmethod
    def _role_value(role: Any) -> str:
        return str(getattr(role, "value", role))

    def refine(
        self,
        history: list[dict],
        *,
        mentee_id: str,
        force_finalize: bool = False,
        revision_instruction: str = "",
    ) -> RefineResult:
        try:
            module = importlib.import_module("agents.question_refine_agent")
            db_module = importlib.import_module("db.json_db")
            agent = module.QuestionRefineAgent(mentee_id=mentee_id)
            normalized = [
                {
                    "role": self._role_value(item["role"]),
                    "content": str(item["content"]),
                }
                for item in history
            ]
            agent.turn_count = sum(1 for item in normalized if item["role"] == "user")

            if force_finalize:
                agent.messages = [agent.messages[0], *normalized]
                if revision_instruction:
                    agent.messages.append(
                        {
                            "role": "user",
                            "content": (
                                "방금 정제된 질문에 다음 수정 의견을 반영해 다시 "
                                f"정제해 주세요.\n수정 의견: {revision_instruction}"
                            ),
                        }
                    )
                message = agent._finalize()
            else:
                if not normalized or normalized[-1]["role"] != "user":
                    raise ValueError("마지막 상담 메시지는 user 역할이어야 합니다.")
                latest = normalized[-1]["content"]
                previous = normalized[:-1]
                agent.messages = [agent.messages[0], *previous]
                agent.turn_count = sum(
                    1 for item in previous if item["role"] == "user"
                )
                message = agent.chat(latest)

            if not agent.is_done:
                return RefineResult(
                    need_more_info=True,
                    assistant_message=message,
                )

            core_session = db_module.get_session(agent.session_id) or {}
            raw = dict(core_session)
            raw["coreSessionId"] = agent.session_id
            return RefineResult(
                need_more_info=False,
                refined_question=core_session.get(
                    "refined_question", getattr(agent, "refined_question", "")
                ),
                conversation_summary=core_session.get(
                    "conversation_summary",
                    getattr(agent, "conversation_summary", ""),
                ),
                safe_context=core_session.get(
                    "safe_context", getattr(agent, "safe_context", "")
                ),
                search_query=core_session.get(
                    "search_query", getattr(agent, "search_query", "")
                ),
                match_query=core_session.get(
                    "match_query", getattr(agent, "match_query", "")
                ),
                current_bottleneck=core_session.get(
                    "current_bottleneck",
                    getattr(agent, "current_bottleneck", ""),
                ),
                expected_answer_type=core_session.get(
                    "expected_answer_type",
                    getattr(agent, "expected_answer_type", ""),
                ),
                question_units=core_session.get("question_units", []),
                taxonomy_tags=core_session.get("taxonomy_tags", {}),
                routing_hints=core_session.get("routing_hints", {}),
                hard_case_flags=core_session.get("hard_case_flags", {}),
                raw=raw,
            )
        except DomainError:
            raise
        except Exception as exc:
            logger.exception("Agent 1 실행 실패")
            raise DomainError(
                "AGENT1_EXECUTION_FAILED",
                "질문 정제 Agent 실행에 실패했습니다.",
                503,
            ) from exc

    def ensure_core_session(
        self,
        *,
        mentee_id: str,
        core_session_id: str | None,
        refined_question: str,
        conversation_summary: str,
        context: dict,
    ) -> str:
        try:
            db_module = importlib.import_module("db.json_db")
            updates = {
                "refined_question": refined_question,
                "conversation_summary": conversation_summary,
                "safe_context": context.get("safe_context", ""),
                "search_query": context.get("search_query") or refined_question,
                "match_query": context.get("match_query") or refined_question,
                "current_bottleneck": context.get("current_bottleneck", ""),
                "expected_answer_type": context.get("expected_answer_type", ""),
                "question_units": context.get("question_units", []),
                "taxonomy_tags": context.get("taxonomy_tags", {}),
                "routing_hints": context.get("routing_hints", {}),
                "hard_case_flags": context.get("hard_case_flags", {}),
            }
            if core_session_id and db_module.update_session(core_session_id, updates):
                return core_session_id
            created = db_module.create_question_session(
                mentee_id=mentee_id,
                **updates,
            )
            return created["session_id"]
        except Exception as exc:
            logger.exception("Agent 세션 동기화 실패")
            raise DomainError(
                "AGENT_SESSION_SYNC_FAILED",
                "상담 정보를 Agent 세션으로 전달하지 못했습니다.",
                503,
            ) from exc

    def route(self, *, core_session_id: str, refined_question: str, context: dict) -> dict:
        try:
            module = importlib.import_module("agents.search_verify_agent")
            return module.SearchVerifyAgent().run(
                session_id=core_session_id,
                refined_question=refined_question,
                conversation_summary=context.get("conversation_summary", ""),
                routing_hints=context.get("routing_hints", {}),
                search_query=context.get("search_query"),
                safe_context=context.get("safe_context"),
                current_bottleneck=context.get("current_bottleneck"),
                expected_answer_type=context.get("expected_answer_type"),
                question_units=context.get("question_units", []),
                hard_case_flags=context.get("hard_case_flags", {}),
            )
        except Exception as exc:
            logger.exception("Agent 2 실행 실패")
            raise DomainError(
                "AGENT2_EXECUTION_FAILED",
                "검색·검증 Agent 실행에 실패했습니다.",
                503,
            ) from exc

    def recommend_mentors(
        self,
        *,
        core_session_id: str,
        refined_question: str,
        context: dict,
        agent2_result: dict,
        mentee_profile: dict | None = None,
    ) -> dict:
        try:
            main_module = importlib.import_module("main")
            mentor_module = importlib.import_module("agents.mentor_match_agent")
            constraints = main_module.build_mentee_constraints(
                {
                    "refined_question": refined_question,
                    "safe_context": context.get("safe_context", ""),
                    "match_query": context.get("match_query"),
                    "routing_hints": context.get("routing_hints", {}),
                    "taxonomy_tags": context.get("taxonomy_tags", {}),
                    "hard_case_flags": context.get("hard_case_flags", {}),
                    "current_bottleneck": context.get("current_bottleneck", ""),
                    "expected_answer_type": context.get("expected_answer_type", ""),
                    "question_units": context.get("question_units", []),
                    "risk_flags": context.get("hard_case_flags", {}).get(
                        "risk_flags", []
                    ),
                },
                agent2_result,
                mentee_profile,
            )
            return mentor_module.MentorMatchAgent().run(
                session_id=core_session_id,
                refined_question=refined_question,
                conversation_summary=context.get("safe_context", ""),
                mentee_constraints=constraints,
            )
        except Exception as exc:
            logger.exception("Agent 3 실행 실패")
            raise DomainError(
                "AGENT3_EXECUTION_FAILED",
                "멘토 매칭 Agent 실행에 실패했습니다.",
                503,
            ) from exc

    def get_mentor(self, mentor_id: str) -> dict | None:
        try:
            db_module = importlib.import_module("db.json_db")
            return db_module.get_mentor(mentor_id)
        except Exception as exc:
            logger.exception("멘토 페르소나 조회 실패")
            raise DomainError(
                "MENTOR_PERSONA_READ_FAILED",
                "멘토 페르소나 정보를 읽지 못했습니다.",
                503,
            ) from exc

    def generate_persona_answer(
        self,
        *,
        mentor_id: str,
        refined_question: str,
        safe_context: str,
        current_bottleneck: str = "",
        expected_answer_type: str = "",
        bridge_hypothesis: str = "",
        transferable_skills: list[str] | None = None,
        question_units: list[dict] | None = None,
        recommendation_reason: str = "",
    ) -> dict:
        try:
            module = importlib.import_module("agents.mentor_persona_agent")
            result = module.MentorPersonaAgent().run(
                mentor_id=mentor_id,
                refined_question=refined_question,
                context=safe_context,
                current_bottleneck=current_bottleneck,
                expected_answer_type=expected_answer_type,
                bridge_hypothesis=bridge_hypothesis,
                transferable_skills=transferable_skills or [],
                question_units=question_units or [],
                recommendation_reason=recommendation_reason,
            )
            if result is None:
                raise RuntimeError("멘토 페르소나 Agent가 답변을 생성하지 못했습니다.")
            return {
                "mentor_id": result["mentor_id"],
                "content": result["answer_content"],
                "summary": result["answer_summarize"],
                "model": getattr(module.MentorPersonaAgent, "MODEL", "gpt-4.1-mini"),
            }
        except Exception as exc:
            logger.exception("AI 멘토 페르소나 답변 생성 실패")
            raise DomainError(
                "PERSONA_ANSWER_GENERATION_FAILED",
                "AI 멘토 페르소나 답변 생성에 실패했습니다.",
                503,
            ) from exc

    def assetize(self, **kwargs: Any) -> dict:
        try:
            module = importlib.import_module("agents.assetize")
            return module.AssetizeAgent().run(**kwargs)
        except Exception as exc:
            logger.exception("Agent 4 실행 실패")
            raise DomainError(
                "AGENT4_EXECUTION_FAILED",
                "답변 자산화 Agent 실행에 실패했습니다.",
                503,
            ) from exc

    def withdraw_asset(self, answer_id: str) -> bool:
        try:
            db_module = importlib.import_module("db.json_db")
            return db_module.update_by_id(
                "mentor_answers.json",
                "answer_id",
                answer_id,
                {
                    "is_assetized": False,
                    "embedding": None,
                    "reuse_consent_withdrawn": True,
                },
            )
        except Exception as exc:
            logger.exception("Agent 자산 재사용 철회 실패")
            raise DomainError(
                "AGENT_ASSET_WITHDRAWAL_FAILED",
                "기존 Agent 자산에서 답변을 제외하지 못했습니다.",
                503,
            ) from exc


def build_agent_adapter(settings: Settings) -> CoreMentoringAgentAdapter:
    return CoreMentoringAgentAdapter(settings)
