from __future__ import annotations

from uuid import uuid4

import pytest

from app.services.mentoring_agent_adapter import RefineResult


class FakeMentoringAgentAdapter:
    """API 테스트가 실제 OpenAI를 호출하지 않도록 하는 연결 계층 대역."""

    def refine(
        self,
        history: list[dict],
        *,
        mentee_id: str,
        force_finalize: bool = False,
        revision_instruction: str = "",
    ) -> RefineResult:
        user_messages = [
            item for item in history if str(getattr(item["role"], "value", item["role"])) == "user"
        ]
        if len(user_messages) < 2 and not force_finalize:
            return RefineResult(
                need_more_info=True,
                assistant_message="현재 상태와 준비 경험, 목표 기간을 알려주세요.",
            )
        suffix = f" ({revision_instruction})" if revision_instruction else ""
        return RefineResult(
            need_more_info=False,
            refined_question=(
                "6개월 안에 데이터 분석가로 취업하기 위한 기술과 "
                f"포트폴리오 준비 순서는 무엇인가요?{suffix}"
            ),
            conversation_summary="비전공 직무 전환과 포트폴리오 준비 상담",
            safe_context="비전공자이며 Python 기초 프로젝트 경험이 있음",
            search_query="비전공 데이터 분석가 취업 준비 포트폴리오",
            match_query="데이터 분석 직무 전환 경험 멘토",
            current_bottleneck="전환논리_부족",
            expected_answer_type="실행 순서와 경험 기반 조언",
            question_units=[{"question": "무엇을 어떤 순서로 준비해야 하나요?"}],
            taxonomy_tags={"domain_tags": ["데이터분석"]},
            routing_hints={
                "search_strategy_hint": "mentor_first",
                "search_strategy_confidence": 0.9,
                "target_role": "데이터 분석가",
            },
            hard_case_flags={"risk_flags": []},
            raw={"coreSessionId": f"ses_test_{uuid4().hex[:8]}"},
        )

    def ensure_core_session(self, **kwargs) -> str:
        return kwargs.get("core_session_id") or f"ses_test_{uuid4().hex[:8]}"

    def route(self, **kwargs) -> dict:
        return {
            "verdict": "mentor_needed",
            "answer": None,
            "fallback_type": "test",
            "fallback_reason": "개인 상황에 맞는 경험 기반 판단이 필요합니다.",
            "mentor_match_hints": {},
            "retrieval_log": {},
        }

    def recommend_mentors(self, **kwargs) -> dict:
        return {
            "top3": [
                {
                    "mentor_id": f"mr_test_{rank}",
                    "rank": rank,
                    "algorithm_score": 0.9 - (rank * 0.1),
                    "recommendation_reason": "데이터 직무 전환 경험이 질문과 맞습니다.",
                }
                for rank in range(1, 4)
            ]
        }

    def get_mentor(self, mentor_id: str) -> dict:
        rank = mentor_id.rsplit("_", 1)[-1]
        return {
            "mentor_id": mentor_id,
            "mentor_info": {"name": f"테스트 멘토 {rank}"},
            "background": {"status": "직장인"},
            "current_role": "데이터 분석가",
            "years_of_experience": 5,
            "matching_summary_text": "비전공자 직무 전환과 포트폴리오 상담 경험",
            "be_go": "데이터 분석 직무 전환 멘티에게 적합",
            "active": True,
        }

    def generate_persona_answer(self, **kwargs) -> dict:
        content = (
            "저는 실제 사람이 아닌 AI 멘토 페르소나입니다. 먼저 목표 채용공고를 "
            "분석해 반복되는 기술을 정리하고, Python과 SQL 기초를 작은 프로젝트로 "
            "증명하세요. 이후 문제 정의, 데이터 정제, 분석 결과, 의사결정을 하나의 "
            "포트폴리오 이야기로 연결하세요. 매주 결과물을 점검하면서 부족한 기술을 "
            "다음 주 학습 계획에 반영하는 방식으로 진행하는 것이 좋습니다."
        )
        return {
            "content": content,
            "summary": "채용공고 분석부터 포트폴리오 완성까지 단계적으로 준비합니다.",
            "model": "fake-agent",
        }

    def assetize(self, **kwargs) -> dict:
        return {
            "answer_id": f"ans_core_{uuid4().hex[:8]}",
            "question_content": kwargs["question_content"],
            "answer_content": kwargs["answer_content"],
            "embedding": [0.1, 0.2, 0.3],
            "is_assetized": True,
            "reject_reasons": {},
        }

    def withdraw_asset(self, answer_id: str) -> bool:
        return bool(answer_id)


@pytest.fixture(autouse=True)
def use_fake_mentoring_agents(
    monkeypatch: pytest.MonkeyPatch,
) -> type[FakeMentoringAgentAdapter]:
    from app.api.v1 import feedback
    from app.services import agent_pipeline, consultation_service

    factory = lambda settings: FakeMentoringAgentAdapter()  # noqa: E731, ARG005
    monkeypatch.setattr(consultation_service, "build_agent_adapter", factory)
    monkeypatch.setattr(agent_pipeline, "build_agent_adapter", factory)
    monkeypatch.setattr(feedback, "build_agent_adapter", factory)
    return FakeMentoringAgentAdapter
