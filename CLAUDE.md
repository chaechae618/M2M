# M2M (맨투맨) — AI 진로 멘토링 서비스

막연한 진로 고민을 구조화 → 기존 멘토 답변 자산으로 답변 가능한지 검증 → 부족하면 멘토(현재는 AI 페르소나) 연결 → 답변을 다시 자산화하는 파이프라인.

## 레포 구조와 소유권 규칙

| 디렉터리 | 역할 |
|---|---|
| `M2M-mentoring-agent/` | AI 판단 로직 전부. 프롬프트·에이전트·임베딩·평가 |
| `BE/` | FastAPI. 인증 / HTTP / SQL 상태 관리 **only** |
| `FE/` | Next.js 16 + React 19 |

**규칙: 판단 로직과 프롬프트는 `M2M-mentoring-agent/`에만 둔다.**
BE는 `app/services/mentoring_agent_adapter.py`를 통해 호출만 한다. BE 안에 프롬프트 문자열이나 점수 계산 로직을 새로 추가하지 말 것.

```
FastAPI → Agent 1 → Agent 2 → Agent 3 → 페르소나 답변 → Agent 4
```

## 어디를 읽어야 하는가

작업 시작 전에 전체를 훑지 말고 해당하는 것만 읽는다.

**에이전트 로직 수정**
- Agent 1 질문 정제: `M2M-mentoring-agent/agents/question_refine_agent.py` (890줄)
- Agent 2 검색·검증·분기: `agents/search_verify_agent.py` (1335줄, 가장 복잡)
- Agent 3 멘토 매칭: `agents/mentor_match_agent.py` (547줄)
- Agent 4 자산화: `agents/assetize.py` (497줄)
- 페르소나 답변: `agents/mentor_persona_agent.py`
- 상세 설계 근거는 `M2M-mentoring-agent/README.md`에 있다. 에이전트 동작을 바꾸기 전에 해당 섹션을 읽을 것.

**BE 작업**
- 엔드포인트: `BE/app/api/v1/{auth,mentees,consultations,personas,feedback,qna,jobs}.py`
- 파이프라인 오케스트레이션: `BE/app/services/agent_pipeline.py`
- 에이전트 호출 경계: `BE/app/services/mentoring_agent_adapter.py`
- 상태값 정의: `BE/app/models/enums.py` — **여기부터 읽으면 도메인이 빨리 파악된다**

**FE 작업**
- `FE/AGENTS.md`를 먼저 따를 것. Next.js 16은 학습 데이터와 다르므로 `node_modules/next/dist/docs/` 확인 후 코드 작성.
- 구조: `src/app`(라우트) / `src/features` / `src/widgets` / `src/shared`
- 라우트 그룹: `(auth)` `(public)` `(service)`

## 실행

```bash
# BE (BE/ 에서)
python -m uvicorn app.main:app --reload    # http://localhost:8000/docs

# BE 테스트 — conftest.py 테스트 대역 사용, OpenAI 호출/비용 없음
pytest

# FE (FE/ 에서)
npm run dev                                 # http://localhost:3000
```

변경 후에는 `pytest`(BE) 또는 `npm run build`(FE)로 검증한다.

## 규약

- API prefix: `/api/v1`. 응답은 `SuccessResponse[T]` 래퍼로 감싼다 (`app/schemas/common.py`).
- API 요청/응답 필드는 **camelCase**, Python 내부는 snake_case. Pydantic `alias` + `populate_by_name`으로 변환한다.
- 인증: JWT (access/refresh). `CurrentUser` 의존성 사용.
- 에이전트 간 데이터는 정해진 JSON 스키마로 주고받는다. 텍스트 재해석 없이 다음 에이전트의 코드 입력이 되므로 스키마 변경 시 소비하는 쪽을 함께 확인할 것.
- DB: 로컬 SQLite, 개발 모드에서 시작 시 테이블 자동 생성. Alembic 마이그레이션은 아직 미확정.

## 제품 모델 — 실제 멘토는 참여하지 않는다

**"멘토 연결"은 사람에게 넘기는 것이 아니라, 멘토 맥락을 LLM 페르소나에 실어 즉석에서 답변을 생성하는 것이다.** 동아리 시연용 프로젝트이며 실제 현직자가 답변하거나 커피챗을 진행하는 시나리오는 없다.

따라서 다음은 **의도된 설계이지 누락이 아니다** — 되돌리려 하지 말 것:

- `UserRole`에 `MENTEE`만 존재 (멘토는 로그인 주체가 아님)
- `ConsultationStatus`가 `persona_recommended → persona_answer_generating → persona_answered`로 흐름 (사람의 답변 대기 상태 없음)
- 멘토 수락/거절, 커피챗 일정, 실제 멘토 답변 대기 엔드포인트 없음

UI에서 "멘토 답변 대기"에 해당하는 상태는 `PERSONA_ANSWER_GENERATING`이다. 이걸 사람 대기가 아니라 **생성 중 로딩 상태**로 다룬다.

## 현재 상태 (2026-08 기준)

- **FE는 BE에 대부분 연결되어 있다.** `FE/src/shared/api/client.ts`의 `apiRequest()`가 `FE/src/app/api/backend/[...path]/route.ts`(BFF 프록시, 쿠키에 JWT 보관)를 통해 실제 FastAPI를 호출한다. 로그인/회원가입, 상담 챗 전체 플로우, Q&A 게시판, 마이페이지, 사이드바(사용자 이름·최근 대화)까지 연결 완료.
- 아직 연결 안 된 화면: `mentors`/`mentors/[mentorId]`(멘토 카탈로그·상세), `answers/[answerId]`(답변 단건 조회), `forgot-password`(비밀번호 재설정), Q&A 스크랩, 프로필 이미지 업로드 — **전부 BE에 해당 엔드포인트 자체가 없어서** 못 붙인 것이지 FE가 안 붙인 게 아니다.
- 미구현 BE 엔드포인트: 비밀번호 찾기·재설정, Q&A 스크랩, 이름 변경(`MenteeProfileUpdateRequest`에 `name` 없음), 업로드 파일 삭제, 멘토 카탈로그/상세 조회, 답변 단건 조회.
- 페르소나 멘토는 세션 단위 Top-3 추천(`/consultations/{id}/persona-recommendations`)만 있다. 사용자가 전체 목록을 둘러보고 직접 검색·선택하는 카탈로그 엔드포인트는 없다.

## 함정

- `data_db/`는 사용하지 않는 초기 잔재다. 실제 데이터는 `M2M-mentoring-agent/json_db/`에 있다.
- `json_db/mentor_answers.json`은 9.5MB(임베딩 포함)다. 통째로 읽지 말고 스크립트로 처리할 것. Agent 2가 검색하는 실제 자산 DB이며 **180건**: 원본 잇다 Q&A 140건(`itda_1`~`itda_140`, 2026-07-13) + IT개발 도메인 보강 40건(`itda_141`~`itda_180`, `domain_tags: "it개발-추가본"`, 2026-07-25 추가). 파일 상단 `description`/`version`(`itda_140_v1`) 메타는 40건 추가 후 갱신 안 돼서 여전히 140건 기준으로 적혀있다 — 믿지 말 것. `M2M-mentoring-agent/README.md`의 "50건"도 마찬가지로 오래된 값.
- Agent 2 검색 임계값(`SIM_THRESHOLD`, `agents/search_verify_agent.py:452`)은 0.55로 꽤 엄격하다. 180건이 있어도 domain_tags에 없는 니치한 도메인 질문(예: 공공사업개발, 사회학 계열)은 유사도가 안 나와서 `no_similar_answers`로 정상적으로 멘토 매칭행 처리된다 — 데이터 부족 버그가 아님.
- `BE/README.md`의 실행 경로(`D:\ai rookie\...`)는 오래된 값이다.
- BE README가 참조하는 `../docs/` API 명세서는 레포에 없다. 명세가 필요하면 사용자에게 요청할 것.
- 루트의 `제목 없음 *.csv`는 `example_data.csv`의 사본으로 보인다.
