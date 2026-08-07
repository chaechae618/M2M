from math import ceil

from fastapi import APIRouter, Query

from app.api.deps import AppSettings, CurrentUser
from app.core.exceptions import DomainError
from app.schemas.common import SuccessResponse
from app.services.mentoring_agent_adapter import build_agent_adapter

router = APIRouter(prefix="/personas", tags=["AI Mentor Personas"])


def persona_data(mentor: dict, *, experiences: list[dict] | None = None) -> dict[str, object]:
    info = mentor.get("mentor_info", {}) or {}
    background = mentor.get("background", {}) or {}
    return {
        "personaId": mentor.get("mentor_id"),
        "displayName": info.get("name", "AI 멘토"),
        "gender": info.get("gender"),
        "age": info.get("age"),
        "background": {
            "school": background.get("school"),
            "major": background.get("major"),
            "status": background.get("status"),
        },
        "currentRole": mentor.get("current_role", ""),
        "yearsOfExperience": mentor.get("years_of_experience", 0),
        "profileSummary": mentor.get("matching_summary_text", ""),
        "suitableFor": mentor.get("be_go", ""),
        "domainTags": mentor.get("domain_tags", []),
        "experiences": experiences if experiences is not None else [],
        "active": bool(mentor.get("active", True)),
        "isAiPersona": True,
    }


@router.get("", response_model=SuccessResponse[dict[str, object]])
def list_personas(
    current_user: CurrentUser,
    settings: AppSettings,
    query: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> SuccessResponse[dict[str, object]]:
    _ = current_user
    adapter = build_agent_adapter(settings)
    mentors = [item for item in adapter.list_mentors() if item.get("active", True)]
    if query:
        keyword = query.strip().lower()

        def searchable(item: dict) -> bool:
            info = item.get("mentor_info", {}) or {}
            background = item.get("background", {}) or {}
            values = [
                info.get("name", ""),
                background.get("school", ""),
                background.get("major", ""),
                item.get("current_role", ""),
                item.get("matching_summary_text", ""),
                item.get("be_go", ""),
                " ".join(item.get("domain_tags", []) or []),
            ]
            return keyword in " ".join(str(value) for value in values).lower()

        mentors = [item for item in mentors if searchable(item)]

    total = len(mentors)
    start = (page - 1) * limit
    items = mentors[start : start + limit]
    total_pages = ceil(total / limit) if total else 0
    return SuccessResponse(
        data={
            "items": [persona_data(item) for item in items],
            "pagination": {
                "currentPage": page,
                "totalPages": total_pages,
                "totalItems": total,
                "hasNext": page < total_pages,
                "hasPrev": page > 1,
            },
            "disclaimer": "목록의 멘토는 실제 계정이 아닌 AI 멘토 페르소나입니다.",
        }
    )


@router.get("/{persona_id}", response_model=SuccessResponse[dict[str, object]])
def get_persona(
    persona_id: str,
    current_user: CurrentUser,
    settings: AppSettings,
) -> SuccessResponse[dict[str, object]]:
    _ = current_user
    adapter = build_agent_adapter(settings)
    mentor = adapter.get_mentor(persona_id)
    if mentor is None or not mentor.get("active", True):
        raise DomainError("PERSONA_NOT_FOUND", "AI 멘토 페르소나를 찾을 수 없습니다.", 404)
    return SuccessResponse(
        data={
            **persona_data(
                mentor,
                experiences=adapter.get_mentor_experiences(persona_id),
            ),
            "disclaimer": "이 프로필은 실제 멘토 계정이 아닌 AI 페르소나입니다.",
        }
    )
