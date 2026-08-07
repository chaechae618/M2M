from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.mentees import UPLOAD_ROOT
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import app
from app.services.auth_service import AuthService
from tests.test_full_pipeline import create_refined_consultation, signup


def test_name_change_and_password_reset() -> None:
    email = f"account-{uuid4()}@example.com"
    old_password = "password123!"
    new_password = "new-password123!"

    with TestClient(app) as client:
        auth = client.post(
            "/api/v1/auth/signup",
            json={
                "email": email,
                "password": old_password,
                "name": "기존 이름",
                "currentStatus": "job_seeker",
                "termsConsent": True,
                "privacyConsent": True,
            },
        ).json()["data"]
        headers = {"Authorization": f"Bearer {auth['accessToken']}"}

        name_response = client.patch(
            "/api/v1/auth/me",
            headers=headers,
            json={"name": "변경한 이름"},
        )
        assert name_response.status_code == 200
        assert name_response.json()["data"]["name"] == "변경한 이름"

        forgot_response = client.post(
            "/api/v1/auth/password/forgot",
            json={"email": email},
        )
        assert forgot_response.status_code == 200
        assert forgot_response.json()["data"]["emailSent"] is False
        with SessionLocal() as db:
            reset_token, _ = AuthService(db, get_settings()).request_password_reset(email)
        assert reset_token

        unknown_response = client.post(
            "/api/v1/auth/password/forgot",
            json={"email": f"unknown-{uuid4()}@example.com"},
        )
        assert unknown_response.status_code == 200
        assert unknown_response.json()["data"]["accepted"] is True
        assert "resetToken" not in unknown_response.json()["data"]

        reset_response = client.post(
            "/api/v1/auth/password/reset",
            json={"token": reset_token, "newPassword": new_password},
        )
        assert reset_response.status_code == 200

        old_login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": old_password},
        )
        assert old_login.status_code == 401
        new_login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": new_password},
        )
        assert new_login.status_code == 200

        reused_token = client.post(
            "/api/v1/auth/password/reset",
            json={"token": reset_token, "newPassword": old_password},
        )
        assert reused_token.status_code == 400


def test_persona_catalog_and_coffee_chat_crud() -> None:
    with TestClient(app) as client:
        auth = signup(client, "added-api")
        headers = {"Authorization": f"Bearer {auth['accessToken']}"}

        catalog_response = client.get("/api/v1/personas?limit=2", headers=headers)
        assert catalog_response.status_code == 200
        assert len(catalog_response.json()["data"]["items"]) == 2
        persona_id = catalog_response.json()["data"]["items"][0]["personaId"]

        detail_response = client.get(f"/api/v1/personas/{persona_id}", headers=headers)
        assert detail_response.status_code == 200
        assert detail_response.json()["data"]["isAiPersona"] is True
        assert detail_response.json()["data"]["experiences"]

        session_id = create_refined_consultation(client, headers)
        confirm_response = client.post(
            f"/api/v1/consultations/{session_id}/confirm",
            headers={**headers, "Idempotency-Key": str(uuid4())},
            json={"confirmed": True},
        )
        assert confirm_response.status_code == 202
        recommendations = client.get(
            f"/api/v1/consultations/{session_id}/persona-recommendations",
            headers=headers,
        ).json()["data"]["personas"]

        create_response = client.post(
            f"/api/v1/consultations/{session_id}/coffee-chat-requests",
            headers=headers,
            json={
                "personaId": recommendations[0]["personaId"],
                "requestMessage": "직무 전환 경험을 바탕으로 구체적인 조언을 받고 싶습니다.",
            },
        )
        assert create_response.status_code == 201
        request_id = create_response.json()["data"]["requestId"]
        assert create_response.json()["data"]["status"] == "requested"

        update_response = client.patch(
            f"/api/v1/coffee-chat-requests/{request_id}",
            headers=headers,
            json={
                "personaId": recommendations[1]["personaId"],
                "requestMessage": "수정된 질문으로 포트폴리오 조언을 받고 싶습니다.",
            },
        )
        assert update_response.status_code == 200
        assert (
            update_response.json()["data"]["persona"]["personaId"]
            == recommendations[1]["personaId"]
        )

        list_response = client.get("/api/v1/coffee-chat-requests", headers=headers)
        assert list_response.status_code == 200
        assert any(item["requestId"] == request_id for item in list_response.json()["data"])

        cancel_response = client.delete(
            f"/api/v1/coffee-chat-requests/{request_id}",
            headers=headers,
        )
        assert cancel_response.status_code == 200
        assert cancel_response.json()["data"]["status"] == "cancelled"


def test_resume_upload_and_delete() -> None:
    with TestClient(app) as client:
        auth = signup(client, "file-delete")
        headers = {"Authorization": f"Bearer {auth['accessToken']}"}

        upload_response = client.post(
            "/api/v1/mentees/me/resume",
            headers=headers,
            files={"file": ("resume.pdf", b"%PDF-test-delete", "application/pdf")},
        )
        assert upload_response.status_code == 200
        upload_url = upload_response.json()["data"]["url"]
        upload_path = UPLOAD_ROOT / Path(upload_url).relative_to("/uploads")
        assert upload_path.exists()

        delete_response = client.delete("/api/v1/mentees/me/resume", headers=headers)
        assert delete_response.status_code == 200
        assert delete_response.json()["data"]["deleted"] is True
        assert not upload_path.exists()

        profile_response = client.get("/api/v1/mentees/me", headers=headers)
        assert profile_response.json()["data"]["resumeUrl"] is None
