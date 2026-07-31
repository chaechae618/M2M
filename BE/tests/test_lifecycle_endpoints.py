from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.consultation import ConsultationSession
from app.models.enums import ConsultationStatus, JobStatus
from app.models.job import AsyncJob


def signup(client: TestClient, prefix: str) -> dict:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"{prefix}-{uuid4()}@example.com",
            "password": "password123!",
            "name": "생명주기테스트",
            "currentStatus": "job_seeker",
            "termsConsent": True,
            "privacyConsent": True,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def create_refined_consultation(client: TestClient, headers: dict) -> str:
    create_response = client.post(
        "/api/v1/consultations",
        headers=headers,
        json={"initialMessage": "비전공자의 데이터 분석 취업 준비 순서가 궁금합니다."},
    )
    session_id = create_response.json()["data"]["session"]["id"]
    message_response = client.post(
        f"/api/v1/consultations/{session_id}/messages",
        headers=headers,
        json={
            "content": (
                "Python 프로젝트가 있고 6개월 안에 취업하기 위한 "
                "포트폴리오 전략을 알고 싶습니다."
            )
        },
    )
    assert message_response.json()["data"]["sessionStatus"] == "awaiting_confirmation"
    return session_id


def test_complete_answered_consultation() -> None:
    with TestClient(app) as client:
        auth = signup(client, "complete")
        headers = {"Authorization": f"Bearer {auth['accessToken']}"}
        session_id = create_refined_consultation(client, headers)

        confirm_response = client.post(
            f"/api/v1/consultations/{session_id}/confirm",
            headers=headers,
        )
        assert confirm_response.status_code == 202

        recommendations = client.get(
            f"/api/v1/consultations/{session_id}/persona-recommendations",
            headers=headers,
        ).json()["data"]["personas"]
        selection_response = client.post(
            f"/api/v1/consultations/{session_id}/persona-selection",
            headers=headers,
            json={"personaId": recommendations[0]["personaId"]},
        )
        assert selection_response.status_code == 202

        complete_response = client.post(
            f"/api/v1/consultations/{session_id}/complete",
            headers=headers,
        )
        assert complete_response.status_code == 200
        data = complete_response.json()["data"]
        assert data["status"] == "completed"
        assert data["completedAt"] is not None

        repeated_response = client.post(
            f"/api/v1/consultations/{session_id}/complete",
            headers=headers,
        )
        assert repeated_response.status_code == 200


def test_retry_failed_analysis_job() -> None:
    with TestClient(app) as client:
        auth = signup(client, "retry")
        headers = {"Authorization": f"Bearer {auth['accessToken']}"}
        session_id = create_refined_consultation(client, headers)
        confirm_response = client.post(
            f"/api/v1/consultations/{session_id}/confirm",
            headers=headers,
        )
        job_id = confirm_response.json()["data"]["jobId"]

        with SessionLocal() as db:
            job = db.get(AsyncJob, job_id)
            session = db.get(ConsultationSession, session_id)
            job.status = JobStatus.FAILED
            job.current_step = "failed"
            job.error = {
                "code": "AI_SERVICE_TIMEOUT",
                "message": "테스트용 실패",
                "retryable": True,
            }
            session.status = ConsultationStatus.FAILED
            db.commit()

        retry_response = client.post(
            f"/api/v1/jobs/{job_id}/retry",
            headers=headers,
        )
        assert retry_response.status_code == 202
        retry_data = retry_response.json()["data"]
        assert retry_data["jobId"] == job_id
        assert retry_data["status"] == "queued"
        assert retry_data["currentStep"] == "waiting_for_agent2"

        completed_job = client.get(
            f"/api/v1/jobs/{job_id}",
            headers=headers,
        ).json()["data"]
        assert completed_job["status"] == "completed"
        assert completed_job["progress"] == 100

        duplicate_retry = client.post(
            f"/api/v1/jobs/{job_id}/retry",
            headers=headers,
        )
        assert duplicate_retry.status_code == 409
        assert duplicate_retry.json()["error"]["code"] == "JOB_NOT_FAILED"
