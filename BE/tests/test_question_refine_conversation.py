from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
AGENT_ROOT = Path(__file__).resolve().parents[2] / "M2M-mentoring-agent"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from agents import question_refine_agent as module  # noqa: E402


def _completion(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_general_information_keeps_conversation_open(monkeypatch) -> None:
    agent = module.QuestionRefineAgent(mentee_id="mentee-test")
    monkeypatch.setattr(
        agent,
        "_decide_next_action",
        lambda: "answer_directly",
    )
    monkeypatch.setattr(
        module.client.chat.completions,
        "create",
        lambda **kwargs: _completion("MLOps의 주요 업무를 설명해드릴게요."),
    )

    response = agent.chat("MLOps의 주요 업무가 궁금해")

    assert "주요 업무" in response
    assert agent.is_done is False
    assert agent.messages[-1]["role"] == "assistant"


def test_explicit_mentor_consent_finalizes(monkeypatch) -> None:
    agent = module.QuestionRefineAgent(mentee_id="mentee-test")
    monkeypatch.setattr(
        agent,
        "_decide_next_action",
        lambda: "finalize",
    )
    monkeypatch.setattr(agent, "_finalize", lambda: "멘토에게 보낼 질문을 정리했어요.")

    response = agent.chat("좋아, 그 질문으로 멘토에게 연결해줘")

    assert response == "멘토에게 보낼 질문을 정리했어요."


def test_fallback_routes_common_intents_without_auto_finalizing() -> None:
    general = module.QuestionRefineAgent(mentee_id="mentee-general")
    general.messages.append(
        {"role": "user", "content": "데이터사이언스 4학년인데 MLOps의 주요 업무가 궁금해"}
    )
    assert general._fallback_next_action() == "answer_directly"

    personal = module.QuestionRefineAgent(mentee_id="mentee-personal")
    personal.messages.append(
        {"role": "user", "content": "제 포트폴리오로 MLOps 취업이 가능할까요?"}
    )
    assert personal._fallback_next_action() == "offer_mentor"

    consent = module.QuestionRefineAgent(mentee_id="mentee-consent")
    consent.messages.append(
        {"role": "user", "content": "좋아, MLOps 현직자에게 물어볼래"}
    )
    assert consent._fallback_next_action() == "finalize"

    short_consent = module.QuestionRefineAgent(mentee_id="mentee-short-consent")
    short_consent.messages.extend(
        [
            {"role": "assistant", "content": "멘토에게 보낼 질문으로 정리할까요?"},
            {"role": "user", "content": "응"},
        ]
    )
    assert short_consent._fallback_next_action() == "finalize"
