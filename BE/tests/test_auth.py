from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_signup_login_refresh_and_logout() -> None:
    email = f"mentee-{uuid4()}@example.com"
    password = "password123!"

    with TestClient(app) as client:
        signup_response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": email,
                "password": password,
                "name": "김멘티",
                "currentStatus": "student",
                "targetRoles": ["프로덕트 매니저"],
                "interestDomains": ["IT"],
                "termsConsent": True,
                "privacyConsent": True,
            },
        )
        assert signup_response.status_code == 201
        signup_data = signup_response.json()["data"]
        assert signup_data["user"]["role"] == "mentee"
        assert signup_data["user"]["profileCompleted"] is True

        access_token = signup_data["accessToken"]
        refresh_token = signup_data["refreshToken"]

        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["data"]["email"] == email

        profile_response = client.get(
            "/api/v1/mentees/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert profile_response.json()["data"]["targetRoles"] == ["프로덕트 매니저"]
        assert profile_response.json()["data"]["interestDomains"] == ["IT"]

        duplicate_response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": email,
                "password": password,
                "name": "김멘티",
                "currentStatus": "student",
                "termsConsent": True,
                "privacyConsent": True,
            },
        )
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["error"]["code"] == "EMAIL_EXISTS"

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_response.status_code == 200

        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refreshToken": refresh_token},
        )
        assert refresh_response.status_code == 200
        rotated_refresh_token = refresh_response.json()["data"]["refreshToken"]

        logout_response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"refreshToken": rotated_refresh_token},
        )
        assert logout_response.status_code == 200
        assert logout_response.json()["data"]["loggedOut"] is True
