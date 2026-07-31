from uuid import uuid4

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
