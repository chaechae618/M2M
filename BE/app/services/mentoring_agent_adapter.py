"""FastAPI와 M2M-mentoring-agent 사이의 얇은 연결 계층."""

from __future__ import annotations

import importlib
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

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


class DemoMentoringAgentAdapter:
    """API 키 없이 제품의 전체 상담 흐름을 확인하는 로컬 대역."""

    _mentors = {
        "mr_demo_pm": {
            "mentor_id": "mr_demo_pm",
            "mentor_info": {"name": "김도윤"},
            "background": {"status": "현직자", "company": "테크 스타트업"},
            "current_role": "프로덕트 매니저",
            "years_of_experience": 7,
            "domain_tags": ["커리어 전환", "서비스 기획", "포트폴리오"],
            "matching_summary_text": "비전공자의 직무 전환과 포트폴리오 설계를 돕습니다.",
            "be_go": "막연한 고민을 실행 가능한 준비 순서로 바꾸는 데 적합합니다.",
            "active": True,
        },
        "mr_demo_data": {
            "mentor_id": "mr_demo_data",
            "mentor_info": {"name": "박서연"},
            "background": {"status": "현직자", "company": "데이터 플랫폼 기업"},
            "current_role": "데이터 분석가",
            "years_of_experience": 6,
            "domain_tags": ["데이터 분석", "직무 전환", "프로젝트"],
            "matching_summary_text": "학습 내용을 채용 가능한 프로젝트로 연결해 왔습니다.",
            "be_go": "준비 경험을 구체적인 결과물과 일정으로 정리하는 데 적합합니다.",
            "active": True,
        },
        "mr_demo_career": {
            "mentor_id": "mr_demo_career",
            "mentor_info": {"name": "이현우"},
            "background": {"status": "현직자", "company": "커리어 교육 기업"},
            "current_role": "커리어 코치",
            "years_of_experience": 8,
            "domain_tags": ["취업 준비", "이력서", "면접"],
            "matching_summary_text": "지원 전략과 경험 정리를 함께 점검합니다.",
            "be_go": "현재 고민의 우선순위와 다음 행동을 정하는 데 적합합니다.",
            "active": True,
        },
    }

    def refine(
        self,
        history: list[dict],
        *,
        mentee_id: str,
        force_finalize: bool = False,
        revision_instruction: str = "",
    ) -> RefineResult:
        user_messages = [
            str(item["content"]).strip()
            for item in history
            if CoreMentoringAgentAdapter._role_value(item["role"]) == "user"
        ]
        if len(user_messages) < 2 and not force_finalize:
            return RefineResult(
                need_more_info=True,
                assistant_message=(
                    "고민을 더 구체적으로 정리해볼게요. 현재 상황과 이미 "
                    "시도해본 것, 가장 원하는 결과를 알려주세요."
                ),
            )

        original = user_messages[0] if user_messages else "커리어 고민"
        detail = user_messages[-1] if user_messages else original
        refined_question = self._question_from(detail)
        if revision_instruction:
            refined_question = (
                f"{refined_question.rstrip('?')} - {revision_instruction.strip()}을 "
                "반영하면 어떻게 준비하는 것이 좋을까요?"
            )
        return RefineResult(
            need_more_info=False,
            refined_question=refined_question,
            conversation_summary=f"{original}에 관해 현재 상황과 원하는 결과를 상담함",
            safe_context=detail,
            search_query=refined_question,
            match_query=f"{original} 경험이 있는 커리어 멘토",
            current_bottleneck="우선순위와 실행 계획이 구체적이지 않음",
            expected_answer_type="경험에 기반한 실행 순서와 점검 기준",
            question_units=[{"question": refined_question}],
            taxonomy_tags={"domain_tags": ["커리어", "취업 준비"]},
            routing_hints={
                "search_strategy_hint": "mentor_first",
                "search_strategy_confidence": 0.9,
            },
            hard_case_flags={"risk_flags": []},
            raw={"coreSessionId": f"ses_demo_{uuid4().hex[:10]}"},
        )

    @staticmethod
    def _question_from(detail: str) -> str:
        normalized = detail.strip().rstrip(".!? ")
        if not normalized:
            normalized = "현재 커리어 고민"
        return f"{normalized} 상황에서 무엇부터 어떤 순서로 준비하는 것이 좋을까요?"

    def ensure_core_session(self, **kwargs: Any) -> str:
        return kwargs.get("core_session_id") or f"ses_demo_{uuid4().hex[:10]}"

    def route(self, **kwargs: Any) -> dict:
        return {
            "verdict": "mentor_needed",
            "answer": None,
            "fallback_type": "demo",
            "fallback_reason": "개인 경험에 기반한 조언이 필요한 질문입니다.",
            "mentor_match_hints": {},
            "retrieval_log": {"mode": "demo"},
        }

    def recommend_mentors(self, **kwargs: Any) -> dict:
        return {
            "top3": [
                {
                    "mentor_id": mentor_id,
                    "rank": rank,
                    "algorithm_score": 1.0 - rank * 0.1,
                    "recommendation_reason": mentor["be_go"],
                }
                for rank, (mentor_id, mentor) in enumerate(
                    self._mentors.items(), start=1
                )
            ]
        }

    def get_mentor(self, mentor_id: str) -> dict | None:
        return self._mentors.get(mentor_id)

    def generate_persona_answer(self, **kwargs: Any) -> dict:
        question = kwargs.get("refined_question", "현재 고민")
        content = (
            "저는 실제 사람이 아닌 AI 멘토 페르소나입니다.\n\n"
            f"## 고민 정리\n{question}\n\n"
            "## 추천 순서\n"
            "1. 원하는 결과와 기한을 한 문장으로 적어보세요.\n"
            "2. 현재 가진 경험을 결과물 중심으로 세 가지까지 정리하세요.\n"
            "3. 부족한 역량은 작은 프로젝트로 검증하고 매주 결과를 남기세요.\n\n"
            "처음부터 완벽한 계획을 만들기보다, 이번 주에 끝낼 수 있는 결과물 "
            "하나를 정하고 피드백을 받는 방식이 가장 현실적입니다."
        )
        return {
            "content": content,
            "summary": "목표를 정한 뒤 경험 정리와 작은 프로젝트를 순서대로 진행합니다.",
            "model": "m2m-demo-agent",
        }

    def assetize(self, **kwargs: Any) -> dict:
        return {
            "answer_id": f"ans_demo_{uuid4().hex[:10]}",
            "question_content": kwargs["question_content"],
            "answer_content": kwargs["answer_content"],
            "embedding": [0.1, 0.2, 0.3],
            "is_assetized": True,
            "reject_reasons": {},
        }

    def withdraw_asset(self, answer_id: str) -> bool:
        return bool(answer_id)


MentoringAgentAdapter = CoreMentoringAgentAdapter | DemoMentoringAgentAdapter


def build_agent_adapter(settings: Settings) -> MentoringAgentAdapter:
    mode = settings.mentoring_agent_mode
    if mode == "demo" or (mode == "auto" and not settings.openai_api_key):
        logger.info("M2M Agent를 데모 모드로 실행합니다.")
        return DemoMentoringAgentAdapter()
    if not settings.openai_api_key:
        raise DomainError(
            "OPENAI_API_KEY_MISSING",
            "실제 Agent 실행을 위한 OPENAI_API_KEY가 설정되지 않았습니다.",
            503,
        )
    return CoreMentoringAgentAdapter(settings)
