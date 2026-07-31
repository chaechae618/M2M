from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def signup(client: TestClient, name: str) -> dict:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"qna-{uuid4()}@example.com",
            "password": "password123!",
            "name": name,
            "currentStatus": "student",
            "termsConsent": True,
            "privacyConsent": True,
        },
    )
    return response.json()["data"]


def test_qna_auth_and_author_permissions() -> None:
    with TestClient(app) as client:
        unauthenticated = client.get("/api/v1/qna/posts")
        assert unauthenticated.status_code == 401

        first = signup(client, "첫번째")
        second = signup(client, "두번째")
        first_headers = {"Authorization": f"Bearer {first['accessToken']}"}
        second_headers = {"Authorization": f"Bearer {second['accessToken']}"}

        create_response = client.post(
            "/api/v1/qna/posts",
            headers=first_headers,
            json={
                "category": "직무·취업",
                "title": "비전공자 데이터 분석 준비",
                "content": "비전공자가 데이터 분석을 준비할 때 어떤 순서가 좋을까요?",
                "anonymous": False,
            },
        )
        assert create_response.status_code == 201
        post_id = create_response.json()["data"]["id"]

        list_response = client.get("/api/v1/qna/posts", headers=second_headers)
        assert list_response.status_code == 200
        assert any(item["id"] == post_id for item in list_response.json()["data"]["items"])

        forbidden_response = client.patch(
            f"/api/v1/qna/posts/{post_id}",
            headers=second_headers,
            json={"title": "다른 사용자가 수정"},
        )
        assert forbidden_response.status_code == 403

        comment_response = client.post(
            f"/api/v1/qna/posts/{post_id}/comments",
            headers=second_headers,
            json={"content": "채용공고 분석부터 시작해 보세요.", "anonymous": True},
        )
        assert comment_response.status_code == 201
        comment_id = comment_response.json()["data"]["id"]
        assert comment_response.json()["data"]["author"]["anonymous"] is True

        comment_forbidden = client.delete(
            f"/api/v1/qna/posts/{post_id}/comments/{comment_id}",
            headers=first_headers,
        )
        assert comment_forbidden.status_code == 403

        delete_comment = client.delete(
            f"/api/v1/qna/posts/{post_id}/comments/{comment_id}",
            headers=second_headers,
        )
        assert delete_comment.status_code == 200

        delete_post = client.delete(
            f"/api/v1/qna/posts/{post_id}",
            headers=first_headers,
        )
        assert delete_post.status_code == 200
