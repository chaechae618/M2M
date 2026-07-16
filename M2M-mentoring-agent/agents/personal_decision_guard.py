"""Rule-based guard for personal career decision questions.

This guard catches high-risk questions that combine personal context with
choice/decision requests. Those cases should be routed to a mentor before
retrieval/verifier scores can promote them to llm_direct.
"""

from __future__ import annotations

import re


PERSONAL_CONTEXT_TRIGGERS = [
    "제 상황",
    "내 상황",
    "저의 상황",
    "현재 경력",
    "경력을 버리고",
    "인턴 경험 없음",
    "인턴 경험이 없",
    "비전공자",
    "나이",
    "학점",
    "스펙",
    "경력",
]

DECISION_REQUEST_TRIGGERS = [
    "결정해 주세요",
    "결정해주세요",
    "선택해 주세요",
    "선택해주세요",
    "뭐가 맞을까요",
    "어떤 게 맞을까요",
    "어떻게 해야 할까요",
    "어떻게 해야할까요",
    "해야 할지",
    "해야할지",
    "지원할지",
    "갈지",
    "맞을지",
    "나을까요",
]

CAREER_HIGH_RISK_TRIGGERS = [
    "전환",
    "전향",
    "신입",
    "경력직",
    "퇴사",
    "이직",
    "휴학",
    "진학",
    "포기",
    "재지원",
]


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _contains_any(text: str, triggers: list[str]) -> bool:
    compact_text = _compact(text)
    return any(_compact(trigger) in compact_text for trigger in triggers)


def requires_personal_decision_guard(question: str) -> tuple[bool, dict]:
    """Return whether a question should be hard-routed to mentor_needed."""

    has_personal_context = _contains_any(question, PERSONAL_CONTEXT_TRIGGERS)
    has_decision_request = _contains_any(question, DECISION_REQUEST_TRIGGERS)
    has_high_risk_career_choice = _contains_any(question, CAREER_HIGH_RISK_TRIGGERS)

    triggered = {
        "has_personal_context": has_personal_context,
        "has_decision_request": has_decision_request,
        "has_high_risk_career_choice": has_high_risk_career_choice,
    }
    should_block = (
        has_personal_context
        and has_decision_request
        and has_high_risk_career_choice
    )
    return should_block, triggered


def personal_decision_guard_flag(question: str) -> dict:
    """Build a hard_case_flags-compatible payload."""

    should_block, triggered = requires_personal_decision_guard(question)
    return {
        "requires_personal_decision": should_block,
        "personal_decision_guard": triggered,
        "personal_decision_reason": (
            "개인 상황 기반 선택/결정이 필요한 질문입니다."
            if should_block
            else ""
        ),
    }
