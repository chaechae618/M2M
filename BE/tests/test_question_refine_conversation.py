from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
AGENT_ROOT = Path(__file__).resolve().parents[2] / "M2M-mentoring-agent"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from agents import question_refine_agent as question_module  # noqa: E402
from agents import search_verify_agent as router_module  # noqa: E402


def _completion(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _fake_finalize(agent: question_module.QuestionRefineAgent) -> str:
    agent.is_done = True
    return "정제 질문을 Agent 2로 전달했습니다."


def test_explicit_mentor_request_skips_sufficiency_check(monkeypatch) -> None:
    agent = question_module.QuestionRefineAgent(mentee_id="mentee-test")

    def fail_if_called() -> tuple[bool, str]:
        raise AssertionError("명시적 연결 요청에는 충분성 검사를 호출하면 안 됩니다.")

    monkeypatch.setattr(agent, "_check_sufficiency", fail_if_called)
    monkeypatch.setattr(agent, "_finalize", lambda: _fake_finalize(agent))

    response = agent.chat("정보가 부족한 건 알겠는데 아무튼 멘토 연결해줘")

    assert response == "정제 질문을 Agent 2로 전달했습니다."
    assert agent.explicit_mentor_request is True
    assert agent.is_done is True


def test_explicit_mentor_request_phrases() -> None:
    assert question_module.QuestionRefineAgent._has_explicit_mentor_request(
        "현직자에게 물어볼래"
    )
    assert question_module.QuestionRefineAgent._has_explicit_mentor_request(
        "멘토한테 보내줘"
    )
    assert question_module.QuestionRefineAgent._has_explicit_mentor_request("연결해줘")
    assert not question_module.QuestionRefineAgent._has_explicit_mentor_request(
        "비전공자도 취업할 수 있을까요?"
    )
    assert not question_module.QuestionRefineAgent._has_explicit_mentor_request(
        "멘토 연결은 싫어요"
    )


def test_insufficient_question_asks_evaluator_followup(monkeypatch) -> None:
    agent = question_module.QuestionRefineAgent(mentee_id="mentee-test")

    def insufficient() -> tuple[bool, str]:
        agent.next_best_question = "현재 준비한 경험이나 프로젝트가 있나요?"
        return False, "ask_followup"

    monkeypatch.setattr(agent, "_check_sufficiency", insufficient)
    monkeypatch.setattr(
        question_module.client.chat.completions,
        "create",
        lambda **kwargs: _completion(
            "현재 준비한 경험이나 프로젝트가 있다면 알려주세요."
        ),
    )

    response = agent.chat("데이터 분석가가 되고 싶어요.")

    assert "경험이나 프로젝트" in response
    assert agent.is_done is False
    assert agent.messages[-1]["role"] == "assistant"


def test_sufficient_question_finalizes(monkeypatch) -> None:
    agent = question_module.QuestionRefineAgent(mentee_id="mentee-test")
    monkeypatch.setattr(
        agent,
        "_check_sufficiency",
        lambda: (True, "ready_for_refinement"),
    )
    monkeypatch.setattr(agent, "_finalize", lambda: _fake_finalize(agent))

    response = agent.chat(
        "경영학과 졸업생이고 Python 프로젝트가 있습니다. "
        "6개월 안에 데이터 분석가 취업을 위한 포트폴리오 전략이 궁금합니다."
    )

    assert response == "정제 질문을 Agent 2로 전달했습니다."
    assert agent.is_done is True


def test_three_followups_then_finalize_even_if_still_insufficient(monkeypatch) -> None:
    agent = question_module.QuestionRefineAgent(mentee_id="mentee-test")
    agent.turn_count = agent.max_turns - 1
    monkeypatch.setattr(
        agent,
        "_check_sufficiency",
        lambda: (False, "ask_followup"),
    )
    monkeypatch.setattr(agent, "_finalize", lambda: _fake_finalize(agent))

    response = agent.chat("잘 모르겠어요.")

    assert response == "정제 질문을 Agent 2로 전달했습니다."
    assert agent.is_done is True


def test_personalized_question_requires_personal_context(monkeypatch) -> None:
    agent = question_module.QuestionRefineAgent(mentee_id="mentee-test")
    evaluator_result = {
        "fields": {
            "관심_직무": {"score": 0.9, "evidence": "데이터 분석가"},
            "현재_상태": {"score": 0.2, "evidence": ""},
            "보유_경험": {"score": 0.2, "evidence": ""},
            "묻고_싶은_내용": {"score": 0.9, "evidence": "취업 전략"},
            "제약_조건": {"score": 0.2, "evidence": ""},
        },
        "question_quality": {
            "specificity": 0.9,
            "mentor_answerability": 0.9,
            "priority_clarity": 0.9,
        },
        "intent_router": {
            "question_maturity": "focused",
            "context_requirement": "personalized",
            "needs_clarification": False,
            "next_action": "ready_for_refinement",
        },
        "next_best_question": "현재 상황과 관련 경험을 알려주세요.",
    }
    monkeypatch.setattr(
        question_module.client.chat.completions,
        "create",
        lambda **kwargs: _completion(
            json.dumps(evaluator_result, ensure_ascii=False)
        ),
    )

    sufficient, action = agent._check_sufficiency()

    assert sufficient is False
    assert action == "ask_followup"
    assert agent.next_best_question == "현재 상황과 관련 경험을 알려주세요."


def test_finalize_preserves_explicit_mentor_request_routing_hint(monkeypatch) -> None:
    agent = question_module.QuestionRefineAgent(mentee_id="mentee-test")
    agent.explicit_mentor_request = True
    refinement = {
        "user_facing": {
            "refined_question": "데이터 분석가 취업 방향을 멘토에게 묻고 싶습니다.",
            "conversation_summary": "정보는 부족하지만 사용자가 연결을 요청했습니다.",
        },
        "agent_context": {
            "search_query": "데이터 분석가 취업",
            "match_query": "데이터 분석가 취업 멘토",
            "safe_context": "데이터 분석가 취업에 관심이 있습니다.",
            "taxonomy_tags": {},
            "routing_hints": {
                "desired_help": "취업 전략",
                "search_strategy_hint": "search_first",
                "search_strategy_confidence": 0.4,
            },
        },
        "diagnostics": {},
    }
    saved: dict = {}

    def save_session(**kwargs):
        saved.update(kwargs)
        return {"session_id": "session-test"}

    monkeypatch.setattr(agent, "_generate_refinement", lambda fix_hint="": refinement)
    monkeypatch.setattr(agent, "_check_refinement_quality", lambda result: (True, ""))
    monkeypatch.setattr(question_module, "create_question_session", save_session)

    agent._finalize()

    assert saved["routing_hints"]["explicit_mentor_request"] is True
    assert saved["routing_hints"]["search_strategy_hint"] == "mentor_first"
    assert saved["routing_hints"]["search_strategy_confidence"] == 1.0


def test_agent2_routes_explicit_request_to_mentor(monkeypatch) -> None:
    monkeypatch.setattr(router_module, "update_session", lambda *args, **kwargs: None)
    agent = router_module.SearchVerifyAgent()

    result = agent.run(
        session_id="session-test",
        refined_question="데이터 분석가 취업 방향을 멘토에게 묻고 싶습니다.",
        conversation_summary="사용자가 멘토 연결을 명시적으로 요청했습니다.",
        routing_hints={
            "explicit_mentor_request": True,
            "desired_help": "취업 전략",
        },
    )

    assert result["verdict"] == "mentor_needed"
    assert result["fallback_type"] == "explicit_mentor_request"
    assert result["strategy"] == "mentor_first"
