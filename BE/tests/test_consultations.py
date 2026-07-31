from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def signup(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"consultation-{uuid4()}@example.com",
            "password": "password123!",
            "name": "박멘티",
            "currentStatus": "job_seeker",
            "termsConsent": True,
            "privacyConsent": True,
        },
    )
    return response.json()["data"]


def test_consultation_refinement_and_confirm_flow() -> None:
    with TestClient(app) as client:
        auth = signup(client)
        headers = {"Authorization": f"Bearer {auth['accessToken']}"}

        create_response = client.post(
            "/api/v1/consultations",
            headers=headers,
            json={
                "initialMessage": (
                    "비전공자인데 데이터 분석가로 취업하려면 무엇부터 준비해야 하나요?"
                )
            },
        )
        assert create_response.status_code == 201
        session = create_response.json()["data"]["session"]
        session_id = session["id"]
        assert session["status"] == "collecting_context"
        assert session["refinedQuestionRevision"]["used"] == 0

        message_response = client.post(
            f"/api/v1/consultations/{session_id}/messages",
            headers=headers,
            json={
                "content": (
                    "경영학과 졸업생이고 Python 기초 프로젝트 경험이 있으며 "
                    "6개월 안에 취업하고 싶습니다."
                )
            },
        )
        assert message_response.status_code == 200
        assert message_response.json()["data"]["sessionStatus"] == "awaiting_confirmation"

        for expected_used in range(1, 4):
            regenerate_response = client.post(
                f"/api/v1/consultations/{session_id}/refined-question/regenerate",
                headers=headers,
                json={"instruction": f"포트폴리오 준비를 더 강조해주세요. {expected_used}"},
            )
            assert regenerate_response.status_code == 200
            revision = regenerate_response.json()["data"]["refinedQuestionRevision"]
            assert revision["used"] == expected_used

        limit_response = client.post(
            f"/api/v1/consultations/{session_id}/refined-question/regenerate",
            headers=headers,
            json={"instruction": "한 번 더 바꿔주세요."},
        )
        assert limit_response.status_code == 409
        assert (
            limit_response.json()["error"]["code"]
            == "REFINED_QUESTION_REVISION_LIMIT_EXCEEDED"
        )

        direct_edit_response = client.patch(
            f"/api/v1/consultations/{session_id}/refined-question",
            headers=headers,
            json={
                "content": (
                    "6개월 안에 데이터 분석가로 취업하기 위한 기술과 "
                    "포트폴리오 준비 순서를 알려주세요."
                )
            },
        )
        assert direct_edit_response.status_code == 200
        assert (
            direct_edit_response.json()["data"]["refinedQuestionRevision"]["used"] == 3
        )

        confirm_response = client.post(
            f"/api/v1/consultations/{session_id}/confirm",
            headers={**headers, "Idempotency-Key": str(uuid4())},
            json={"confirmed": True},
        )
        assert confirm_response.status_code == 202
        confirm_data = confirm_response.json()["data"]
        assert confirm_data["sessionStatus"] == "analyzing"

        job_response = client.get(
            confirm_data["pollingUrl"],
            headers=headers,
        )
        assert job_response.status_code == 200
        assert job_response.json()["data"]["jobType"] == "consultation_analysis"

        list_response = client.get("/api/v1/consultations", headers=headers)
        assert list_response.status_code == 200
        assert list_response.json()["data"]["pagination"]["totalItems"] >= 1


def test_consultation_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/consultations")
        assert response.status_code == 401
