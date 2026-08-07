"""실제 OpenAI와 M2M Agent 1~4를 FastAPI 경로로 검증한다.

테스트의 Fake Agent를 사용하지 않는다. 개발 DB에 live-agent-* 테스트 계정과
상담/자산화 레코드가 남고 OpenAI API 사용량이 발생한다.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def require(response: object, label: str) -> dict:
    body = response.json()
    if response.status_code >= 400:
        raise RuntimeError(
            f"{label}: HTTP {response.status_code} {body.get('error', {})}"
        )
    return body["data"]


def run() -> None:
    with TestClient(app) as client:
        email = f"live-agent-{uuid4()}@example.com"
        auth = require(
            client.post(
                "/api/v1/auth/signup",
                json={
                    "email": email,
                    "password": "Live-agent-test123!",
                    "name": "라이브 에이전트 검증",
                    "currentStatus": "job_seeker",
                    "termsConsent": True,
                    "privacyConsent": True,
                },
            ),
            "signup",
        )
        headers = {"Authorization": f"Bearer {auth['accessToken']}"}

        created = require(
            client.post(
                "/api/v1/consultations",
                headers=headers,
                json={
                    "initialMessage": (
                        "저는 경영학과 졸업생이고 Python 기초 프로젝트 하나만 있습니다. "
                        "6개월 안에 데이터 분석가로 취업해야 하는데, 제 이력서와 "
                        "포트폴리오 중 무엇을 버리고 무엇을 강조할지 실제 비전공자 전환 "
                        "경험이 있는 멘토의 개인적 판단과 경험을 듣고 싶습니다."
                    )
                },
            ),
            "agent1-create",
        )
        session_id = created["session"]["id"]
        session_status = created["session"]["status"]
        print("AGENT1_CREATE", session_status, session_id, flush=True)

        replies = [
            (
                "현재 이력서에는 경영학 전공, 매출 데이터 분석 Python 프로젝트, SQL "
                "기초를 적었습니다. 포트폴리오는 기술 설명만 길고 비즈니스 문제와 "
                "성과가 약합니다. 특히 실제 서류 검토 경험에 근거해 어떤 프로젝트 "
                "서술을 삭제하거나 보강할지 알고 싶습니다."
            ),
            (
                "목표는 6개월 이내 중소·중견 IT 서비스 기업의 주니어 데이터 "
                "분석가입니다. 하루 4시간 학습 가능하고, 가장 막힌 부분은 비전공 "
                "경력을 직무 역량으로 설득력 있게 연결하는 것입니다."
            ),
            (
                "원하는 답변은 비전공자 전환 사례를 본 멘토의 우선순위 판단, 이력서 "
                "문장 예시, 6개월 실행 순서입니다. 일반적인 도구 목록보다 실제 채용 "
                "관점의 구체적 조언이 필요합니다."
            ),
        ]
        for index, reply in enumerate(replies, 1):
            if session_status == "awaiting_confirmation":
                break
            message = require(
                client.post(
                    f"/api/v1/consultations/{session_id}/messages",
                    headers=headers,
                    json={"content": reply},
                ),
                f"agent1-message-{index}",
            )
            session_status = message["sessionStatus"]
            print(
                "AGENT1_TURN",
                index,
                session_status,
                "need_more=",
                message["needMoreInfo"],
                flush=True,
            )

        if session_status != "awaiting_confirmation":
            raise RuntimeError(f"Agent 1 did not finalize: {session_status}")

        confirmed = require(
            client.post(
                f"/api/v1/consultations/{session_id}/confirm",
                headers={**headers, "Idempotency-Key": str(uuid4())},
                json={"confirmed": True},
            ),
            "agent2-confirm",
        )
        print("AGENT2_JOB", confirmed["jobStatus"], confirmed["jobId"], flush=True)
        result = require(
            client.get(
                f"/api/v1/consultations/{session_id}/result",
                headers=headers,
            ),
            "agent2-result",
        )
        print(
            "AGENT2_RESULT",
            result["status"],
            result["route"],
            result.get("reason"),
            flush=True,
        )
        if result["route"] != "mentor_needed":
            raise RuntimeError(
                "Agent 3~persona live verification requires mentor_needed; "
                f"actual route was {result['route']}"
            )

        recommendations = require(
            client.get(
                f"/api/v1/consultations/{session_id}/persona-recommendations",
                headers=headers,
            ),
            "agent3-recommendations",
        )["personas"]
        print(
            "AGENT3_TOP3",
            len(recommendations),
            [
                (item["rank"], item["personaId"], round(item["matchScore"], 3))
                for item in recommendations
            ],
            flush=True,
        )

        coffee_chat = require(
            client.post(
                f"/api/v1/consultations/{session_id}/coffee-chat-requests",
                headers=headers,
                json={
                    "personaId": recommendations[0]["personaId"],
                    "requestMessage": (
                        "비전공자 전환 경험을 바탕으로 제 서류 우선순위를 "
                        "구체적으로 조언해 주세요."
                    ),
                },
            ),
            "coffee-chat",
        )
        print(
            "COFFEE_CHAT",
            coffee_chat["status"],
            coffee_chat["requestId"],
            flush=True,
        )

        selected = require(
            client.post(
                f"/api/v1/consultations/{session_id}/persona-selection",
                headers={**headers, "Idempotency-Key": str(uuid4())},
                json={"personaId": recommendations[0]["personaId"]},
            ),
            "persona-answer",
        )
        print(
            "PERSONA_JOB",
            selected["jobId"],
            selected["coffeeChatRequestId"],
            flush=True,
        )
        answered = require(
            client.get(
                f"/api/v1/consultations/{session_id}/result",
                headers=headers,
            ),
            "persona-result",
        )
        answer = answered["answer"]
        print(
            "PERSONA_RESULT",
            answered["status"],
            answer["answerType"],
            answer["model"],
            len(answer["content"]),
            flush=True,
        )

        require(
            client.post(
                f"/api/v1/consultations/{session_id}/feedback",
                headers=headers,
                json={
                    "answerId": answer["id"],
                    "rating": 5,
                    "helpfulTags": ["specific", "actionable"],
                    "comment": "라이브 Agent 검증",
                },
            ),
            "feedback",
        )
        asset_job = require(
            client.put(
                f"/api/v1/consultations/{session_id}/reuse-consent",
                headers=headers,
                json={
                    "answerId": answer["id"],
                    "consent": True,
                    "scope": "anonymized_rag",
                },
            ),
            "agent4-consent",
        )
        print("AGENT4_JOB", asset_job["jobId"], flush=True)
        asset = require(
            client.get(
                f"/api/v1/consultations/{session_id}/assetization",
                headers=headers,
            ),
            "agent4-result",
        )
        print(
            "AGENT4_RESULT",
            asset["status"],
            asset["privacyCheck"],
            asset["qualityCheck"],
            asset["embeddingStored"],
            asset["assetId"],
            flush=True,
        )


if __name__ == "__main__":
    run()
