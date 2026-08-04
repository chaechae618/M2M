from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def signup(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"mentee-{uuid4()}@example.com",
            "password": "password123!",
            "name": "김멘티",
            "currentStatus": "student",
            "termsConsent": True,
            "privacyConsent": True,
        },
    )
    return response.json()["data"]


def test_profile_and_experience_crud() -> None:
    with TestClient(app) as client:
        auth = signup(client)
        headers = {"Authorization": f"Bearer {auth['accessToken']}"}

        profile_response = client.get("/api/v1/mentees/me", headers=headers)
        assert profile_response.status_code == 200
        assert profile_response.json()["data"]["currentStatus"] == "student"

        update_response = client.patch(
            "/api/v1/mentees/me",
            headers=headers,
            json={
                "name": "김수정",
                "background": {"school": "M2M대학교", "major": "경영학"},
                "targetRoles": ["데이터 분석가"],
                "interestDomains": ["IT", "금융"],
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["data"]["name"] == "김수정"
        assert update_response.json()["data"]["targetRoles"] == ["데이터 분석가"]

        create_response = client.post(
            "/api/v1/mentees/me/experiences",
            headers=headers,
            json={
                "experienceType": "project",
                "title": "매출 분석 프로젝트",
                "description": "Python으로 매출 데이터를 분석했습니다.",
                "startDate": "2026-01",
                "endDate": "2026-03",
                "keySkills": ["데이터 분석"],
                "tools": ["Python"],
            },
        )
        assert create_response.status_code == 201
        experience_id = create_response.json()["data"]["id"]

        list_response = client.get("/api/v1/mentees/me/experiences", headers=headers)
        assert list_response.status_code == 200
        assert any(item["id"] == experience_id for item in list_response.json()["data"])

        patch_response = client.patch(
            f"/api/v1/mentees/me/experiences/{experience_id}",
            headers=headers,
            json={"role": "분석 담당"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["data"]["role"] == "분석 담당"

        delete_response = client.delete(
            f"/api/v1/mentees/me/experiences/{experience_id}",
            headers=headers,
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["data"]["deleted"] is True


def test_resume_upload_validation() -> None:
    with TestClient(app) as client:
        auth = signup(client)
        headers = {"Authorization": f"Bearer {auth['accessToken']}"}

        response = client.post(
            "/api/v1/mentees/me/resume",
            headers=headers,
            files={"file": ("resume.pdf", b"%PDF-test", "application/pdf")},
        )
        assert response.status_code == 200
        assert response.json()["data"]["fileType"] == "resume"
        assert response.json()["data"]["fileName"] == "resume.pdf"

        profile_response = client.get("/api/v1/mentees/me", headers=headers)
        assert profile_response.json()["data"]["resumeFileName"] == "resume.pdf"

        invalid_response = client.post(
            "/api/v1/mentees/me/resume",
            headers=headers,
            files={"file": ("resume.exe", b"invalid", "application/octet-stream")},
        )
        assert invalid_response.status_code == 400
        assert invalid_response.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_portfolio_accepts_pdf_and_pptx_only() -> None:
    with TestClient(app) as client:
        auth = signup(client)
        headers = {"Authorization": f"Bearer {auth['accessToken']}"}

        for file_name, content_type in [
            ("portfolio.pdf", "application/pdf"),
            (
                "portfolio.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
        ]:
            response = client.post(
                "/api/v1/mentees/me/portfolio",
                headers=headers,
                files={"file": (file_name, b"test", content_type)},
            )
            assert response.status_code == 200
            assert response.json()["data"]["fileType"] == "portfolio"
            assert response.json()["data"]["fileName"] == file_name

            profile_response = client.get("/api/v1/mentees/me", headers=headers)
            assert profile_response.json()["data"]["portfolioFileName"] == file_name

        invalid_response = client.post(
            "/api/v1/mentees/me/portfolio",
            headers=headers,
            files={"file": ("portfolio.docx", b"invalid", "application/octet-stream")},
        )
        assert invalid_response.status_code == 400
        assert invalid_response.json()["error"]["code"] == "INVALID_FILE_TYPE"
