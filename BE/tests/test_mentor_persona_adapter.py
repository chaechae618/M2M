from pathlib import Path
from types import SimpleNamespace

from app.core.config import Settings
from app.services import mentoring_agent_adapter
from app.services.mentoring_agent_adapter import CoreMentoringAgentAdapter


def test_adapter_calls_pulled_mentor_persona_agent(monkeypatch) -> None:
    captured: dict = {}

    class FakeMentorPersonaAgent:
        MODEL = "test-model"

        def run(self, **kwargs):
            captured.update(kwargs)
            return {
                "mentor_id": kwargs["mentor_id"],
                "mentor_name": "테스트 멘토",
                "answer_content": "페르소나가 생성한 테스트 답변입니다.",
                "answer_summarize": "테스트 답변 요약",
            }

    fake_module = SimpleNamespace(MentorPersonaAgent=FakeMentorPersonaAgent)
    monkeypatch.setattr(
        mentoring_agent_adapter.importlib,
        "import_module",
        lambda name: fake_module,
    )
    agent_root = Path(__file__).resolve().parents[2] / "M2M-mentoring-agent"
    adapter = CoreMentoringAgentAdapter(
        Settings(
            _env_file=None,
            jwt_secret_key="x" * 32,
            openai_api_key="test-key",
            mentoring_agent_root=agent_root,
        )
    )

    result = adapter.generate_persona_answer(
        mentor_id="mentor_001",
        refined_question="어떻게 준비해야 하나요?",
        safe_context="비전공 취업 준비",
        current_bottleneck="전환논리_부족",
        expected_answer_type="경험 기반 조언",
        bridge_hypothesis="기존 경험을 분석 역량으로 연결",
        transferable_skills=["문제 해결"],
        question_units=[{"question": "포트폴리오는 어떻게 구성하나요?"}],
        recommendation_reason="비전공 전환 경험이 유사함",
    )

    assert captured == {
        "mentor_id": "mentor_001",
        "refined_question": "어떻게 준비해야 하나요?",
        "context": "비전공 취업 준비",
        "current_bottleneck": "전환논리_부족",
        "expected_answer_type": "경험 기반 조언",
        "bridge_hypothesis": "기존 경험을 분석 역량으로 연결",
        "transferable_skills": ["문제 해결"],
        "question_units": [{"question": "포트폴리오는 어떻게 구성하나요?"}],
        "recommendation_reason": "비전공 전환 경험이 유사함",
    }
    assert result == {
        "mentor_id": "mentor_001",
        "content": "페르소나가 생성한 테스트 답변입니다.",
        "summary": "테스트 답변 요약",
        "model": "test-model",
    }
