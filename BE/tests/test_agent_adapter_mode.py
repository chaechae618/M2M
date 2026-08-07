import pytest

from app.core.config import Settings
from app.core.exceptions import DomainError
from app.services.mentoring_agent_adapter import (
    DemoMentoringAgentAdapter,
    build_agent_adapter,
)


def test_auto_mode_uses_demo_adapter_without_api_key() -> None:
    adapter = build_agent_adapter(
        Settings(mentoring_agent_mode="auto", openai_api_key=None)
    )

    assert isinstance(adapter, DemoMentoringAgentAdapter)
    follow_up = adapter.refine(
        [{"role": "user", "content": "비전공자인데 PM을 준비하고 싶어요."}],
        mentee_id="test-mentee",
    )
    assert follow_up.need_more_info is True

    refined = adapter.refine(
        [
            {"role": "user", "content": "비전공자인데 PM을 준비하고 싶어요."},
            {"role": "assistant", "content": follow_up.assistant_message},
            {"role": "user", "content": "학교 팀 프로젝트 경험이 있어요."},
        ],
        mentee_id="test-mentee",
    )
    assert refined.need_more_info is False
    assert refined.refined_question


def test_live_mode_requires_api_key() -> None:
    with pytest.raises(DomainError) as error:
        build_agent_adapter(
            Settings(mentoring_agent_mode="live", openai_api_key=None)
        )

    assert error.value.code == "OPENAI_API_KEY_MISSING"
