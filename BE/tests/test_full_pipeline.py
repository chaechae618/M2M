from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


def signup(client: TestClient, prefix: str = "pipeline") -> dict:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"{prefix}-{uuid4()}@example.com",
            "password": "password123!",
            "name": "통합멘티",
            "currentStatus": "job_seeker",
            "termsConsent": True,
            "privacyConsent": True,
        },
    )
    return response.json()["data"]


def create_refined_consultation(client: TestClient, headers: dict) -> str:
    response = client.post(
        "/api/v1/consultations",
        headers=headers,
        json={
            "initialMessage": (
                "저는 비전공자인데 데이터 분석가로 전환할 수 있을지 고민하고 있습니다."
            )
        },
    )
    session_id = response.json()["data"]["session"]["id"]
    message_response = client.post(
        f"/api/v1/consultations/{session_id}/messages",
        headers=headers,
        json={
            "content": (
                "Python 기초 프로젝트가 있고 6개월 안에 취업하기 위한 "
                "준비 순서와 포트폴리오 방향을 알고 싶습니다."
            )
        },
    )
    assert message_response.status_code == 200
    assert message_response.json()["data"]["sessionStatus"] == "awaiting_confirmation"
    return session_id


@pytest.mark.parametrize(
    ("verdict", "expected_status", "expects_recommendations"),
    [
        ("llm_direct", "ai_answered", False),
        ("partial_with_mentor_suggest", "persona_recommended", True),
    ],
)
def test_general_answer_route_branches(
    monkeypatch: pytest.MonkeyPatch,
    use_fake_mentoring_agents: type,
    verdict: str,
    expected_status: str,
    expects_recommendations: bool,
) -> None:
    answer_content = "채용공고를 분석한 뒤 Python, SQL, 포트폴리오 순서로 준비하세요."

    def route(_self: object, **_kwargs: object) -> dict:
        return {
            "verdict": verdict,
            "answer": answer_content,
            "avg_score": 0.86,
            "source_trace": {"used_answer_ids": ["asset-test-1"]},
            "fallback_reason": None,
        }

    monkeypatch.setattr(use_fake_mentoring_agents, "route", route)

    with TestClient(app) as client:
        auth = signup(client, f"route-{verdict}")
        headers = {"Authorization": f"Bearer {auth['accessToken']}"}
        session_id = create_refined_consultation(client, headers)

        confirm_response = client.post(
            f"/api/v1/consultations/{session_id}/confirm",
            headers=headers,
        )
        assert confirm_response.status_code == 202

        result = client.get(
            f"/api/v1/consultations/{session_id}/result",
            headers=headers,
        ).json()["data"]
        assert result["status"] == expected_status
        assert result["route"] == verdict
        assert result["answer"]["content"] == answer_content
        assert result["answer"]["source"]["mode"] == "rag_json_db"

        recommendations_response = client.get(
            f"/api/v1/consultations/{session_id}/persona-recommendations",
            headers=headers,
        )
        if expects_recommendations:
            assert recommendations_response.status_code == 200
            assert len(recommendations_response.json()["data"]["personas"]) == 3
        else:
            assert recommendations_response.status_code == 409


def test_persona_feedback_and_assetization_flow() -> None:
    with TestClient(app) as client:
        auth = signup(client)
        headers = {"Authorization": f"Bearer {auth['accessToken']}"}
        session_id = create_refined_consultation(client, headers)

        confirm_response = client.post(
            f"/api/v1/consultations/{session_id}/confirm",
            headers={**headers, "Idempotency-Key": str(uuid4())},
            json={"confirmed": True},
        )
        assert confirm_response.status_code == 202

        result_response = client.get(
            f"/api/v1/consultations/{session_id}/result",
            headers=headers,
        )
        assert result_response.status_code == 200
        assert result_response.json()["data"]["status"] == "persona_recommended"
        assert result_response.json()["data"]["route"] == "mentor_needed"

        analysis_detail = client.get(
            f"/api/v1/consultations/{session_id}",
            headers=headers,
        ).json()["data"]
        assert analysis_detail["latestJob"]["jobType"] == "consultation_analysis"
        assert analysis_detail["latestJob"]["status"] == "completed"
        assert analysis_detail["answer"] is None
        assert analysis_detail["feedback"] is None
        assert analysis_detail["reuseConsent"] is None

        recommendations_response = client.get(
            f"/api/v1/consultations/{session_id}/persona-recommendations",
            headers=headers,
        )
        assert recommendations_response.status_code == 200
        personas = recommendations_response.json()["data"]["personas"]
        assert len(personas) == 3
        assert all(item["isAiPersona"] for item in personas)

        selection_response = client.post(
            f"/api/v1/consultations/{session_id}/persona-selection",
            headers={**headers, "Idempotency-Key": str(uuid4())},
            json={"personaId": personas[0]["personaId"]},
        )
        assert selection_response.status_code == 202

        answer_response = client.get(
            f"/api/v1/consultations/{session_id}/result",
            headers=headers,
        )
        answer_data = answer_response.json()["data"]
        assert answer_data["status"] == "persona_answered"
        assert answer_data["answer"]["answerType"] == "persona_ai"
        assert answer_data["answer"]["model"] == "fake-agent"
        assert (
            answer_data["answer"]["promptVersion"]
            == "m2m-mentor-persona-agent"
        )
        answer_id = answer_data["answer"]["id"]

        answer_detail = client.get(
            f"/api/v1/consultations/{session_id}",
            headers=headers,
        ).json()["data"]
        assert answer_detail["latestJob"]["jobType"] == "persona_answer_generation"
        assert answer_detail["answer"]["id"] == answer_id

        feedback_response = client.post(
            f"/api/v1/consultations/{session_id}/feedback",
            headers=headers,
            json={
                "answerId": answer_id,
                "rating": 5,
                "helpfulTags": ["specific", "actionable"],
                "comment": "준비 순서가 구체적입니다.",
            },
        )
        assert feedback_response.status_code == 201

        feedback_detail = client.get(
            f"/api/v1/consultations/{session_id}",
            headers=headers,
        ).json()["data"]
        assert feedback_detail["feedback"]["rating"] == 5
        assert feedback_detail["reuseConsent"] is None

        consent_response = client.put(
            f"/api/v1/consultations/{session_id}/reuse-consent",
            headers=headers,
            json={
                "answerId": answer_id,
                "consent": True,
                "scope": "anonymized_rag",
            },
        )
        assert consent_response.status_code == 200

        consent_detail = client.get(
            f"/api/v1/consultations/{session_id}",
            headers=headers,
        ).json()["data"]
        assert consent_detail["reuseConsent"]["consent"] is True

        qna_list_response = client.get(
            "/api/v1/qna/posts",
            headers=headers,
            params={"query": "6개월 안에 데이터 분석가", "limit": 10},
        )
        assert qna_list_response.status_code == 200
        qna_items = qna_list_response.json()["data"]["items"]
        created_post = next(
            item
            for item in qna_items
            if item["title"].startswith("6개월 안에 데이터 분석가")
            and "AI 멘토 페르소나" in item["content"]
        )
        assert created_post["author"]["anonymous"] is True

        qna_detail_response = client.get(
            f"/api/v1/qna/posts/{created_post['id']}",
            headers=headers,
        )
        assert qna_detail_response.status_code == 200
        assert qna_detail_response.json()["data"]["id"] == created_post["id"]

        asset_response = client.get(
            f"/api/v1/consultations/{session_id}/assetization",
            headers=headers,
        )
        assert asset_response.status_code == 200
        assert asset_response.json()["data"]["privacyCheck"] == "passed"
        assert asset_response.json()["data"]["qualityCheck"] == "passed"
        assert asset_response.json()["data"]["embeddingStored"] is True

        withdrawal_response = client.put(
            f"/api/v1/consultations/{session_id}/reuse-consent",
            headers=headers,
            json={"answerId": answer_id, "consent": False},
        )
        assert withdrawal_response.status_code == 200
        assert withdrawal_response.json()["data"]["retrievalExcluded"] is True
