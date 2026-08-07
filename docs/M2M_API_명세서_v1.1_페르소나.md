# M2M API 명세서 v1.1 — 페르소나 멘토 구조

## 문서 정보

| 항목 | 내용 |
| --- | --- |
| 서비스명 | M2M (Mentor to Mentee) |
| 문서 버전 | v1.1-draft |
| 작성일 | 2026-07-25 |
| API 버전 | v1 |
| 개발 Base URL | `http://localhost:8000/api/v1` |
| 운영 Base URL | `https://{service-domain}/api/v1` |
| 인증 | 멘티 Bearer Access Token |
| 자동 문서 | `http://localhost:8000/docs` |
| 정정 전 문서 | `M2M_API_명세서_v1.0.md` |

---

## 1. 핵심 전제

### 1.1 사용자와 멘토의 정의

- 서비스에 가입하고 로그인하는 사용자는 멘티뿐이다.
- 멘토는 실제 사람이 아니라 사전에 만든 LLM 페르소나다.
- 멘토 페르소나는 로그인하거나 질문을 수락·거절하지 않는다.
- Agent 2가 `mentor_needed`로 라우팅하면 Agent 3가 적합한 페르소나 Top 3를 추천한다.
- 멘티가 페르소나를 선택하면 해당 페르소나 프롬프트를 적용한 LLM이 답변한다.
- 답변 제공 후 멘티에게 만족도와 재사용 동의를 묻는다.

### 1.2 포함 기능

- 멘티 회원가입·로그인
- 멘티 프로필·경험 관리
- AI 멀티턴 상담
- 정제 질문 확인·직접 수정·최대 3회 재생성
- Agent 2의 `llm_direct` 또는 `mentor_needed` 라우팅
- 일반 AI 직접 답변
- 멘토 페르소나 Top 3 추천·선택
- 선택한 페르소나를 적용한 LLM 답변 생성
- 지난 상담 목록·상세
- 답변 만족도 평가
- 멘티의 답변 재사용 동의
- 동의·개인정보·품질 조건을 충족한 답변 자산화
- 로그인한 멘티 전용 Q&A

### 1.3 사용자와 내부 리소스

| 구분 | 인증 | 설명 |
| --- | --- | --- |
| 멘티 `mentee` | 필요 | 서비스의 유일한 로그인 사용자 |
| 멘토 페르소나 `mentor_persona` | 해당 없음 | 내부 데이터 및 프롬프트 리소스 |
| Agent 1 | 해당 없음 | 추가 정보 수집 및 질문 정제 |
| Agent 2 | 해당 없음 | 검색·검증 및 라우팅 |
| Agent 3 | 해당 없음 | 페르소나 Top 3 추천 |
| 자산화 Agent | 해당 없음 | 개인정보·품질 검사 및 RAG 자산 저장 |

### 1.4 전체 처리 흐름

```text
멘티 자유 질문 입력
  → Agent 1 추가 질문
  → 멘티 답변
  → 필요한 정보가 충분할 때까지 멀티턴 반복
  → 정제 질문 생성
  → 멘티 확인
     ├─ 직접 수정
     ├─ AI 재생성 요청: 최대 3회
     └─ 확정
  → Agent 2 검색·검증·라우팅
     ├─ llm_direct
     │    → 기존 자산을 근거로 일반 AI 답변
     │
     └─ mentor_needed
          → Agent 3 멘토 페르소나 Top 3 추천
          → 멘티가 페르소나 1개 선택
          → 페르소나 프롬프트를 적용한 LLM 답변 생성
  → 멘티에게 답변 전달
  → 만족도 평가
  → 재사용 동의 요청
     ├─ 미동의: 개인 상담 기록으로만 유지
     └─ 동의: 개인정보 검사 + 품질 검사
          → 통과 시 RAG 자산 및 임베딩 저장
```

---

## 2. 확정된 운영 정책

### 2.1 Q&A 접근

- Q&A 목록과 상세 조회 모두 로그인한 멘티만 가능하다.
- Q&A 작성·수정·삭제·댓글도 로그인한 멘티만 가능하다.
- 모든 `/qna/*` API에 멘티 인증이 필요하다.
- 비로그인 요청은 `401 UNAUTHORIZED`를 반환한다.

### 2.2 정제 질문 재생성

- 최초 정제 질문 생성은 재생성 횟수에 포함하지 않는다.
- 멘티가 AI에게 정제 질문 수정을 요청할 때마다 1회 증가한다.
- AI 재생성은 상담 세션당 최대 3회 허용한다.
- 멘티가 정제 질문 텍스트를 직접 수정하는 것은 횟수에 포함하지 않는다.
- 3회를 모두 사용하면 직접 수정 또는 현재 질문 확정만 가능하다.
- 정제 질문을 확정한 이후에는 수정하거나 재생성할 수 없다.

세션 응답에 다음 정보를 포함한다.

```json
{
  "refinedQuestionRevision": {
    "used": 1,
    "limit": 3,
    "remaining": 2,
    "canRegenerate": true,
    "canEditDirectly": true
  }
}
```

재생성 한도 초과:

```json
{
  "success": false,
  "error": {
    "code": "REFINED_QUESTION_REVISION_LIMIT_EXCEEDED",
    "message": "정제 질문 재생성은 최대 3회까지 가능합니다. 직접 수정하거나 현재 질문을 확정해주세요."
  }
}
```

### 2.3 답변 자산화

자산화에는 멘티의 명시적 동의가 필요하다.

```text
멘티 재사용 동의
AND 개인정보 검사 통과
AND 품질 검사 통과
AND 답변이 정상 완료 상태
```

- 실제 멘토가 없으므로 멘토 동의는 받지 않는다.
- 미동의 답변은 다른 사용자 RAG 검색에 사용하지 않는다.
- 동의 철회 시 재사용 자산, 임베딩, 검색 캐시를 제거한다.
- 동의 철회만으로 멘티의 개인 상담 기록까지 삭제하지 않는다.

---

## 3. 상담 세션 상태

| 상태 | 설명 | 다음 가능한 상태 |
| --- | --- | --- |
| `collecting_context` | Agent 1이 추가 정보를 수집하는 중 | `awaiting_confirmation`, `cancelled` |
| `awaiting_confirmation` | 정제 질문 확인 대기 | `collecting_context`, `analyzing`, `cancelled` |
| `analyzing` | Agent 2 검색·검증·라우팅 중 | `ai_answered`, `persona_recommended`, `failed` |
| `ai_answered` | `llm_direct` 답변 생성 완료 | `awaiting_feedback`, `completed` |
| `persona_recommended` | 페르소나 Top 3 추천 완료 | `persona_answer_generating`, `cancelled` |
| `persona_answer_generating` | 선택한 페르소나로 답변 생성 중 | `persona_answered`, `failed` |
| `persona_answered` | 페르소나 답변 생성 완료 | `awaiting_feedback`, `completed` |
| `awaiting_feedback` | 만족도·재사용 동의 입력 대기 | `assetizing`, `completed` |
| `assetizing` | 개인정보·품질 검사 및 자산화 중 | `assetized`, `completed`, `failed` |
| `assetized` | RAG 자산 및 임베딩 저장 완료 | `completed` |
| `completed` | 상담 완료 | 없음 |
| `cancelled` | 멘티가 상담 취소 | 없음 |
| `failed` | AI 또는 저장 처리 실패 | 직전 처리 단계로 재시도 |

운영 규칙:

- 멘티 한 명당 미완료 상담은 최대 3개다.
- `completed`, `cancelled`는 활성 상담 수에 포함하지 않는다.
- 모든 상담·작업 API는 리소스 소유자인 멘티만 접근할 수 있다.

---

## 4. 공통 규칙

### 4.1 인증 헤더

```http
Authorization: Bearer {accessToken}
Content-Type: application/json
```

### 4.2 성공 응답

```json
{
  "success": true,
  "data": {},
  "message": "처리되었습니다.",
  "requestId": "req_01K0ABCD1234"
}
```

### 4.3 오류 응답

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력값을 확인해주세요.",
    "details": [
      {
        "field": "initialMessage",
        "reason": "질문은 10자 이상이어야 합니다."
      }
    ]
  },
  "requestId": "req_01K0ABCD1234"
}
```

### 4.4 날짜·시간

- ISO 8601 UTC 사용
- 예: `2026-07-25T08:30:00Z`

### 4.5 페이지네이션

```text
?page=1&limit=20
```

```json
{
  "pagination": {
    "currentPage": 1,
    "totalPages": 3,
    "totalItems": 42,
    "hasNext": true,
    "hasPrev": false
  }
}
```

### 4.6 비동기 작업

Agent 2 분석, 페르소나 답변 생성, 자산화처럼 오래 걸리는 처리는 `202 Accepted`로 작업 ID를 반환한다.

```json
{
  "success": true,
  "data": {
    "jobId": "job_001",
    "status": "queued",
    "pollingUrl": "/api/v1/jobs/job_001"
  }
}
```

프론트엔드는 1~2초 간격으로 작업 상태를 조회한다.

---

## 5. 엔드포인트 요약

### 5.1 인증

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| POST | `/auth/signup` | 없음 | 멘티 회원가입 |
| POST | `/auth/login` | 없음 | 멘티 로그인 |
| POST | `/auth/refresh` | Refresh Token | Access Token 갱신 |
| POST | `/auth/logout` | 멘티 | 로그아웃 |
| GET | `/auth/me` | 멘티 | 내 계정 조회 |

### 5.2 멘티 프로필·경험

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| GET | `/mentees/me` | 멘티 | 내 프로필 조회 |
| PATCH | `/mentees/me` | 멘티 | 내 프로필 수정 |
| POST | `/mentees/me/resume` | 멘티 | 이력서·경력기술서 업로드 |
| POST | `/mentees/me/portfolio` | 멘티 | 포트폴리오 업로드 |
| GET | `/mentees/me/experiences` | 멘티 | 경험 목록 |
| POST | `/mentees/me/experiences` | 멘티 | 경험 등록 |
| PATCH | `/mentees/me/experiences/{experienceId}` | 멘티 | 경험 수정 |
| DELETE | `/mentees/me/experiences/{experienceId}` | 멘티 | 경험 삭제 |

### 5.3 AI 상담

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| POST | `/consultations` | 멘티 | 상담 생성·첫 질문 전송 |
| GET | `/consultations` | 멘티 | 지난 상담 목록 |
| GET | `/consultations/{sessionId}` | 멘티 | 상담 상세 |
| POST | `/consultations/{sessionId}/messages` | 멘티 | 추가 대화 |
| POST | `/consultations/{sessionId}/refined-question/regenerate` | 멘티 | 정제 질문 AI 재생성 |
| PATCH | `/consultations/{sessionId}/refined-question` | 멘티 | 정제 질문 직접 수정 |
| POST | `/consultations/{sessionId}/confirm` | 멘티 | 정제 질문 확정·Agent 2 시작 |
| GET | `/consultations/{sessionId}/result` | 멘티 | 라우팅·답변 결과 조회 |
| POST | `/consultations/{sessionId}/complete` | 멘티 | 상담 완료 |
| DELETE | `/consultations/{sessionId}` | 멘티 | 상담 취소 |

### 5.4 페르소나 멘토

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| GET | `/consultations/{sessionId}/persona-recommendations` | 멘티 | 페르소나 Top 3 조회 |
| POST | `/consultations/{sessionId}/persona-selection` | 멘티 | 페르소나 선택·답변 생성 |

### 5.5 평가·자산화

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| POST | `/consultations/{sessionId}/feedback` | 멘티 | 답변 만족도 평가 |
| PUT | `/consultations/{sessionId}/reuse-consent` | 멘티 | 재사용 동의 설정·철회 |
| GET | `/consultations/{sessionId}/assetization` | 멘티 | 자산화 상태 조회 |

### 5.6 Q&A

모든 Q&A API는 로그인한 멘티만 접근할 수 있다.

| Method | Endpoint | 설명 |
| --- | --- | --- |
| GET | `/qna/posts` | Q&A 목록·검색 |
| POST | `/qna/posts` | 글 작성 |
| GET | `/qna/posts/{postId}` | 상세·댓글·연관 글 |
| PATCH | `/qna/posts/{postId}` | 글 수정 |
| DELETE | `/qna/posts/{postId}` | 글 삭제 |
| POST | `/qna/images` | 이미지 업로드 |
| POST | `/qna/posts/{postId}/comments` | 댓글 작성 |
| PATCH | `/qna/posts/{postId}/comments/{commentId}` | 댓글 수정 |
| DELETE | `/qna/posts/{postId}/comments/{commentId}` | 댓글 삭제 |

### 5.7 작업

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| GET | `/jobs/{jobId}` | 멘티 | 비동기 작업 상태 |
| POST | `/jobs/{jobId}/retry` | 멘티 | 실패 작업 재시도 |

---

## 6. 인증 API

### 6.1 멘티 회원가입

**Endpoint**: `POST /auth/signup`  
**인증 필요**: 없음

```json
{
  "email": "mentee@example.com",
  "password": "password123!",
  "name": "김멘티",
  "currentStatus": "student",
  "termsConsent": true,
  "privacyConsent": true
}
```

#### Response: 201 Created

```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_001",
      "role": "mentee",
      "email": "mentee@example.com",
      "name": "김멘티",
      "profileCompleted": false,
      "createdAt": "2026-07-25T08:30:00Z"
    },
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "expiresIn": 3600
  }
}
```

### 6.2 로그인

**Endpoint**: `POST /auth/login`

```json
{
  "email": "mentee@example.com",
  "password": "password123!"
}
```

멘티 계정만 로그인할 수 있다.

### 6.3 토큰·내 계정

- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`

---

## 7. 멘티 프로필·경험 API

### 7.1 내 프로필

- `GET /mentees/me`
- `PATCH /mentees/me`

프로필 예시:

```json
{
  "currentStatus": "student",
  "background": {
    "school": "M2M대학교",
    "major": "경영학",
    "grade": "4학년",
    "enrollmentStatus": "enrolled"
  },
  "consideringOptions": ["internship", "full_time"],
  "targetRoles": ["데이터 분석가"],
  "interestDomains": ["IT", "금융"]
}
```

### 7.2 파일 업로드

- `POST /mentees/me/resume`
- `POST /mentees/me/portfolio`

이력서: PDF, DOCX, 최대 10MB  
포트폴리오: PDF, PPTX, 최대 20MB

### 7.3 경험 CRUD

- `GET /mentees/me/experiences`
- `POST /mentees/me/experiences`
- `PATCH /mentees/me/experiences/{experienceId}`
- `DELETE /mentees/me/experiences/{experienceId}`

---

## 8. AI 상담 API

### 8.1 상담 생성

**Endpoint**: `POST /consultations`

```json
{
  "initialMessage": "비전공자인데 데이터 분석가로 취업하려면 무엇부터 준비해야 하나요?"
}
```

#### Response: 201 Created

```json
{
  "success": true,
  "data": {
    "session": {
      "id": "ses_001",
      "title": "비전공자의 데이터 분석가 취업 준비",
      "status": "collecting_context",
      "refinedQuestionRevision": {
        "used": 0,
        "limit": 3,
        "remaining": 3
      },
      "createdAt": "2026-07-25T08:30:00Z"
    },
    "assistantMessage": {
      "id": "msg_001",
      "role": "assistant",
      "content": "현재 전공과 데이터 분석 관련 경험을 알려주세요.",
      "createdAt": "2026-07-25T08:30:02Z"
    }
  }
}
```

### 8.2 추가 메시지 전송

**Endpoint**: `POST /consultations/{sessionId}/messages`

```json
{
  "content": "경영학과 4학년이고 Python 기초 수업과 매출 분석 프로젝트를 해봤어요."
}
```

추가 정보가 필요한 경우:

```json
{
  "success": true,
  "data": {
    "sessionStatus": "collecting_context",
    "needMoreInfo": true,
    "assistantMessage": {
      "id": "msg_002",
      "role": "assistant",
      "content": "목표 취업 시점과 현재 가장 어려운 부분은 무엇인가요?"
    },
    "missingFields": ["target_timeline", "current_bottleneck"]
  }
}
```

정제 질문이 완성된 경우:

```json
{
  "success": true,
  "data": {
    "sessionStatus": "awaiting_confirmation",
    "needMoreInfo": false,
    "refinedQuestion": {
      "content": "경영학과 4학년으로 Python 기초와 매출 분석 프로젝트 경험이 있습니다. 6개월 안에 금융 데이터 분석가 취업을 목표로 할 때 무엇을 어떤 순서로 준비해야 할까요?",
      "conversationSummary": "경영학 전공, Python 기초, 매출 분석 프로젝트 경험, 6개월 내 취업 목표",
      "currentBottleneck": "준비 우선순위 설정",
      "expectedAnswerType": "단계별 준비 계획"
    },
    "refinedQuestionRevision": {
      "used": 0,
      "limit": 3,
      "remaining": 3,
      "canRegenerate": true,
      "canEditDirectly": true
    }
  }
}
```

### 8.3 정제 질문 AI 재생성

**Endpoint**: `POST /consultations/{sessionId}/refined-question/regenerate`

```json
{
  "instruction": "금융권을 목표로 한다는 점과 포트폴리오 준비를 강조해주세요."
}
```

#### Response: 200 OK

```json
{
  "success": true,
  "data": {
    "refinedQuestion": {
      "content": "금융 데이터 분석가를 목표로 하는 경영학과 4학년입니다. 6개월 안에 취업 경쟁력을 갖추려면 금융 데이터 포트폴리오와 기술 역량을 어떤 순서로 준비해야 할까요?"
    },
    "refinedQuestionRevision": {
      "used": 1,
      "limit": 3,
      "remaining": 2,
      "canRegenerate": true,
      "canEditDirectly": true
    }
  }
}
```

적용 규칙:

- 상태가 `awaiting_confirmation`일 때만 가능하다.
- 성공적으로 새 질문이 생성된 경우에만 `used`를 증가시킨다.
- 네트워크·모델 오류로 생성에 실패하면 횟수를 차감하지 않는다.

### 8.4 정제 질문 직접 수정

**Endpoint**: `PATCH /consultations/{sessionId}/refined-question`

```json
{
  "content": "금융 데이터 분석가 취업을 목표로 할 때 6개월 동안 어떤 포트폴리오와 기술을 준비해야 할까요?"
}
```

직접 수정은 재생성 3회 제한에 포함하지 않는다.

### 8.5 정제 질문 확정·Agent 2 실행

**Endpoint**: `POST /consultations/{sessionId}/confirm`  
**권장 헤더**: `Idempotency-Key: {uuid}`

```json
{
  "confirmed": true
}
```

#### Response: 202 Accepted

```json
{
  "success": true,
  "data": {
    "sessionId": "ses_001",
    "sessionStatus": "analyzing",
    "jobId": "job_001",
    "jobStatus": "queued",
    "pollingUrl": "/api/v1/jobs/job_001"
  }
}
```

### 8.6 Agent 2 결과 조회

**Endpoint**: `GET /consultations/{sessionId}/result`

#### `llm_direct`

```json
{
  "success": true,
  "data": {
    "sessionId": "ses_001",
    "status": "ai_answered",
    "route": "llm_direct",
    "answer": {
      "id": "ans_001",
      "answerType": "general_ai",
      "content": "첫 2개월은 SQL과 통계 기초를 보완하고...",
      "confidenceScore": 0.84,
      "reason": "기존 자산에서 충분한 근거를 확인했습니다.",
      "sources": [
        {
          "sourceId": "asset_001",
          "title": "비전공자의 데이터 분석가 준비",
          "whyUsed": "유사한 배경과 목표"
        }
      ]
    }
  }
}
```

#### `mentor_needed`

```json
{
  "success": true,
  "data": {
    "sessionId": "ses_001",
    "status": "persona_recommended",
    "route": "mentor_needed",
    "reason": "개인 전환 경험에 기반한 구체적인 조언이 필요합니다.",
    "recommendationUrl": "/api/v1/consultations/ses_001/persona-recommendations"
  }
}
```

### 8.7 지난 상담

- `GET /consultations`
- `GET /consultations/{sessionId}`

목록 필터:

| 필드 | 허용값 |
| --- | --- |
| `status` | 상담 상태 |
| `route` | `llm_direct`, `mentor_needed` |
| `answerType` | `general_ai`, `persona_ai` |
| `query` | 제목·정제 질문 검색어 |

---

## 9. 페르소나 멘토 API

### 9.1 페르소나 Top 3 조회

**Endpoint**: `GET /consultations/{sessionId}/persona-recommendations`

#### Response: 200 OK

```json
{
  "success": true,
  "data": {
    "sessionId": "ses_001",
    "personas": [
      {
        "rank": 1,
        "personaId": "persona_finance_da_01",
        "displayName": "금융 데이터 분석 멘토",
        "currentRole": "핀테크 데이터 분석가",
        "yearsOfExperience": 6,
        "expertise": ["데이터 분석", "비전공자 전환", "금융"],
        "profileSummary": "경영학 전공 후 금융 데이터 분석가로 전환한 페르소나입니다.",
        "recommendationReason": "멘티와 유사한 전공 배경과 목표 직무 전환 경험을 갖도록 설계된 페르소나입니다.",
        "matchScore": 0.91,
        "personaVersion": "1.2"
      }
    ]
  }
}
```

반드시 화면에 AI 페르소나임을 표시한다.

```text
이 멘토는 실제 인물이 아닌 AI 페르소나입니다.
```

### 9.2 페르소나 선택·답변 생성

**Endpoint**: `POST /consultations/{sessionId}/persona-selection`  
**권장 헤더**: `Idempotency-Key: {uuid}`

```json
{
  "personaId": "persona_finance_da_01"
}
```

#### Response: 202 Accepted

```json
{
  "success": true,
  "data": {
    "sessionId": "ses_001",
    "selectedPersona": {
      "personaId": "persona_finance_da_01",
      "displayName": "금융 데이터 분석 멘토",
      "personaVersion": "1.2"
    },
    "sessionStatus": "persona_answer_generating",
    "jobId": "job_002",
    "pollingUrl": "/api/v1/jobs/job_002"
  }
}
```

### 9.3 페르소나 답변 결과

`GET /consultations/{sessionId}/result`에서 조회한다.

```json
{
  "success": true,
  "data": {
    "sessionId": "ses_001",
    "status": "persona_answered",
    "route": "mentor_needed",
    "answer": {
      "id": "ans_002",
      "answerType": "persona_ai",
      "persona": {
        "personaId": "persona_finance_da_01",
        "displayName": "금융 데이터 분석 멘토",
        "personaVersion": "1.2",
        "isAiPersona": true
      },
      "content": "저와 같은 경영학 배경에서 금융 데이터 분석을 준비한다는 설정으로 조언드리면...",
      "summary": "SQL·통계 기초 → 금융 데이터 프로젝트 → 포트폴리오 개선",
      "generatedAt": "2026-07-25T09:00:00Z"
    }
  }
}
```

페르소나는 실제 경험을 한 사람인 것처럼 허위 사실을 주장하지 않아야 한다. 답변은 다음처럼 표현한다.

- 허용: “이 페르소나의 경력 설정을 기준으로 보면…”
- 금지: “제가 실제로 해당 회사에서 근무했을 때…”

### 9.4 후속 검토: 페르소나 답변 재생성

페르소나 답변 재생성은 v1 구현 범위에 포함하지 않는다. 허용 여부와 최대 횟수를 확정한 뒤 다음 후보 API를 추가할 수 있다.

```http
POST /consultations/{sessionId}/persona-answer/regenerate
```

이 정책은 정제 질문 재생성 최대 3회와는 별개다.

---

## 10. 만족도·동의·자산화 API

### 10.1 만족도 평가

**Endpoint**: `POST /consultations/{sessionId}/feedback`

일반 AI와 페르소나 AI 답변에 동일한 평가 구조를 사용한다.

```json
{
  "answerId": "ans_002",
  "rating": 5,
  "helpfulTags": ["specific", "actionable", "empathetic"],
  "comment": "월별 준비 순서가 구체적이어서 도움이 됐어요."
}
```

평가 데이터에는 다음 분류값을 함께 저장한다.

```json
{
  "route": "mentor_needed",
  "answerType": "persona_ai",
  "personaId": "persona_finance_da_01",
  "personaVersion": "1.2"
}
```

### 10.2 재사용 동의 설정

**Endpoint**: `PUT /consultations/{sessionId}/reuse-consent`

```json
{
  "answerId": "ans_002",
  "consent": true,
  "scope": "anonymized_rag"
}
```

동의하면 자산화 작업을 시작한다.

#### Response: 202 Accepted

```json
{
  "success": true,
  "data": {
    "consent": true,
    "sessionStatus": "assetizing",
    "jobId": "job_003",
    "pollingUrl": "/api/v1/jobs/job_003"
  }
}
```

### 10.3 동의 철회

같은 API에 `consent: false`를 전송한다.

```json
{
  "answerId": "ans_002",
  "consent": false
}
```

#### Response: 200 OK

```json
{
  "success": true,
  "data": {
    "consent": false,
    "retrievalExcluded": true,
    "assetDeleted": true,
    "embeddingDeleted": true,
    "consultationHistoryRetained": true
  }
}
```

### 10.4 자산화 상태 조회

**Endpoint**: `GET /consultations/{sessionId}/assetization`

```json
{
  "success": true,
  "data": {
    "status": "assetized",
    "assetId": "asset_002",
    "privacyCheck": "passed",
    "qualityCheck": "passed",
    "embeddingStored": true,
    "assetizedAt": "2026-07-25T09:10:00Z"
  }
}
```

---

## 11. Q&A API

### 11.1 공통 인증

모든 Q&A API는 다음 헤더가 필요하다.

```http
Authorization: Bearer {accessToken}
```

비로그인 사용자는 목록과 상세도 조회할 수 없다.

### 11.2 Q&A 목록

**Endpoint**: `GET /qna/posts`

Query:

- `query`: 제목·본문 검색
- `category`: 카테고리
- `sort`: `latest`, `popular`, `unanswered`
- `page`, `limit`

### 11.3 Q&A 작성·상세·수정·삭제

- `POST /qna/posts`
- `GET /qna/posts/{postId}`
- `PATCH /qna/posts/{postId}`
- `DELETE /qna/posts/{postId}`

글 작성 예시:

```json
{
  "category": "직무·취업",
  "title": "비전공자인데 PM 준비는 무엇부터 해야 하나요?",
  "content": "현재 경영학과 재학 중이며...",
  "imageIds": ["img_001"],
  "anonymous": false
}
```

### 11.4 이미지·댓글

- `POST /qna/images`
- `POST /qna/posts/{postId}/comments`
- `PATCH /qna/posts/{postId}/comments/{commentId}`
- `DELETE /qna/posts/{postId}/comments/{commentId}`

Q&A에는 실제 멘토 계정이나 멘토 댓글이 존재하지 않는다. 향후 페르소나 자동 답변을 추가한다면 `authorType: "ai_persona"`를 명시하는 별도 API 정책이 필요하다.

---

## 12. 작업 상태 API

### 12.1 작업 조회

**Endpoint**: `GET /jobs/{jobId}`

```json
{
  "success": true,
  "data": {
    "jobId": "job_002",
    "jobType": "persona_answer_generation",
    "status": "processing",
    "progress": 60,
    "currentStep": "answer_generation",
    "createdAt": "2026-07-25T08:40:00Z",
    "updatedAt": "2026-07-25T08:40:05Z"
  }
}
```

작업 종류:

- `consultation_analysis`
- `persona_answer_generation`
- `answer_assetization`
- `resume_extraction`

### 12.2 실패 작업 재시도

**Endpoint**: `POST /jobs/{jobId}/retry`

재시도 가능한 실패 작업만 허용한다.

---

## 13. 주요 오류 코드

### 13.1 인증·권한

| 코드 | HTTP | 설명 |
| --- | --- | --- |
| `UNAUTHORIZED` | 401 | 로그인 필요 |
| `INVALID_CREDENTIALS` | 401 | 계정 정보 불일치 |
| `TOKEN_EXPIRED` | 401 | 토큰 만료 |
| `FORBIDDEN` | 403 | 리소스 접근 권한 없음 |

### 13.2 상담·정제 질문

| 코드 | HTTP | 설명 |
| --- | --- | --- |
| `CONSULTATION_NOT_FOUND` | 404 | 상담 없음 |
| `INVALID_SESSION_STATE` | 409 | 현재 상태에서 실행할 수 없는 요청 |
| `ACTIVE_SESSION_LIMIT_EXCEEDED` | 409 | 활성 상담 3개 초과 |
| `REFINED_QUESTION_NOT_READY` | 409 | 정제 질문 미완성 |
| `REFINED_QUESTION_REVISION_LIMIT_EXCEEDED` | 409 | AI 재생성 3회 초과 |
| `ALREADY_CONFIRMED` | 409 | 이미 정제 질문 확정 |

### 13.3 페르소나

| 코드 | HTTP | 설명 |
| --- | --- | --- |
| `PERSONA_RECOMMENDATION_NOT_READY` | 409 | 페르소나 추천 전 |
| `PERSONA_NOT_FOUND` | 404 | 페르소나 없음 |
| `PERSONA_NOT_RECOMMENDED` | 400 | 추천 Top 3에 없는 페르소나 선택 |
| `PERSONA_ANSWER_GENERATION_FAILED` | 503 | 페르소나 답변 생성 실패 |
| `PERSONA_ANSWER_TIMEOUT` | 504 | 답변 생성 시간 초과 |

### 13.4 평가·자산화

| 코드 | HTTP | 설명 |
| --- | --- | --- |
| `ANSWER_NOT_FOUND` | 404 | 답변 없음 |
| `FEEDBACK_ALREADY_SUBMITTED` | 409 | 이미 만족도 제출 |
| `CONSENT_REQUIRED` | 400 | 재사용 동의값 누락 |
| `ASSETIZATION_NOT_ALLOWED` | 409 | 자산화 조건 미충족 |
| `PRIVACY_CHECK_FAILED` | 409 | 개인정보 검사 실패 |
| `QUALITY_CHECK_FAILED` | 409 | 품질 검사 실패 |

### 13.5 Q&A·서버

| 코드 | HTTP | 설명 |
| --- | --- | --- |
| `QNA_POST_NOT_FOUND` | 404 | 게시글 없음 |
| `QNA_COMMENT_NOT_FOUND` | 404 | 댓글 없음 |
| `RATE_LIMIT_EXCEEDED` | 429 | 호출 횟수 초과 |
| `AI_SERVICE_UNAVAILABLE` | 503 | AI 서비스 이용 불가 |
| `AI_SERVICE_TIMEOUT` | 504 | AI 서비스 시간 초과 |
| `INTERNAL_ERROR` | 500 | 서버 내부 오류 |

---

## 14. 핵심 데이터 모델

### 14.1 상담 세션

```text
consultation_sessions
- id
- mentee_id
- status
- title
- refined_question
- refined_question_revision_count
- route
- selected_persona_id
- selected_persona_version
- created_at
- updated_at
- completed_at
```

### 14.2 페르소나

페르소나는 사용자 테이블에 저장하지 않는다.

```text
mentor_personas
- id
- display_name
- current_role
- years_of_experience
- career_history
- expertise
- profile_summary
- answer_style
- matching_summary
- system_prompt
- version
- active
- created_at
- updated_at
```

### 14.3 답변

```text
answers
- id
- session_id
- answer_type          # general_ai | persona_ai
- route                # llm_direct | mentor_needed
- persona_id           # persona_ai일 때만
- persona_version
- raw_content
- final_content
- summary
- confidence_score
- prompt_version
- model
- created_at
```

### 14.4 자산

```text
answer_assets
- id
- session_id
- answer_id
- anonymized_question
- anonymized_answer
- privacy_check_status
- quality_check_status
- embedding_id
- active
- created_at
- deleted_at
```

---

## 15. 프론트엔드 화면별 API 연결

### 15.1 로그인·회원가입

| 화면 기능 | API |
| --- | --- |
| 멘티 회원가입 | `POST /auth/signup` |
| 로그인 | `POST /auth/login` |
| 로그인 유지 | `POST /auth/refresh` |

### 15.2 메인 상담

| 화면 기능 | API |
| --- | --- |
| 첫 질문 | `POST /consultations` |
| 추가 대화 | `POST /consultations/{sessionId}/messages` |
| 정제 질문 AI 재생성 | `POST /consultations/{sessionId}/refined-question/regenerate` |
| 정제 질문 직접 수정 | `PATCH /consultations/{sessionId}/refined-question` |
| 정제 질문 확정 | `POST /consultations/{sessionId}/confirm` |
| 분석 로딩 | `GET /jobs/{jobId}` |
| 분석·답변 결과 | `GET /consultations/{sessionId}/result` |
| 지난 상담 | `GET /consultations` |

UI에 `재생성 1/3`처럼 사용 횟수를 표시한다.

### 15.3 페르소나 추천

| 화면 기능 | API |
| --- | --- |
| Top 3 카드 | `GET /consultations/{sessionId}/persona-recommendations` |
| 페르소나 선택 | `POST /consultations/{sessionId}/persona-selection` |
| 답변 생성 로딩 | `GET /jobs/{jobId}` |
| 답변 결과 | `GET /consultations/{sessionId}/result` |

각 카드와 답변 화면에 실제 인물이 아닌 AI 페르소나임을 표시한다.

### 15.4 평가·자산화

| 화면 기능 | API |
| --- | --- |
| 만족도 | `POST /consultations/{sessionId}/feedback` |
| 재사용 동의·철회 | `PUT /consultations/{sessionId}/reuse-consent` |
| 자산화 상태 | `GET /consultations/{sessionId}/assetization` |

### 15.5 Q&A

Q&A 진입 시 인증 상태를 검사하며 비로그인 사용자는 로그인 화면으로 이동한다.

---

## 16. TypeScript 핵심 타입

```ts
export type ConsultationStatus =
  | "collecting_context"
  | "awaiting_confirmation"
  | "analyzing"
  | "ai_answered"
  | "persona_recommended"
  | "persona_answer_generating"
  | "persona_answered"
  | "awaiting_feedback"
  | "assetizing"
  | "assetized"
  | "completed"
  | "cancelled"
  | "failed";

export type AnswerRoute = "llm_direct" | "mentor_needed";
export type AnswerType = "general_ai" | "persona_ai";

export interface RefinedQuestionRevision {
  used: number;
  limit: 3;
  remaining: number;
  canRegenerate: boolean;
  canEditDirectly: boolean;
}

export interface MentorPersona {
  rank: number;
  personaId: string;
  displayName: string;
  currentRole: string;
  yearsOfExperience: number;
  expertise: string[];
  profileSummary: string;
  recommendationReason: string;
  matchScore: number;
  personaVersion: string;
  isAiPersona: true;
}

export interface ConsultationAnswer {
  id: string;
  answerType: AnswerType;
  route: AnswerRoute;
  content: string;
  summary?: string;
  persona?: MentorPersona;
  generatedAt: string;
}
```

---

## 17. 보안·AI 투명성

### 17.1 개인정보

- LLM 입력 전에 이메일·전화번호·주소 등 직접 식별자를 제거한다.
- 페르소나 추천에는 정제 질문과 필요한 경력 요약만 사용한다.
- 이력서 원문은 페르소나 답변 프롬프트에 직접 포함하지 않는다.
- 상담 원문과 재사용 자산을 논리적으로 분리한다.

### 17.2 AI 페르소나 표시

- 페르소나를 실제 사람으로 오인하게 만드는 UI·표현을 사용하지 않는다.
- `isAiPersona: true`를 응답에 포함한다.
- 페르소나의 회사·경력·연차는 답변 스타일을 위한 설정임을 화면에 표시한다.
- 페르소나가 실제 경험이나 실재 인맥을 보유한 것처럼 주장하지 않도록 프롬프트와 출력 검사를 적용한다.

### 17.3 관측 정보

다음 항목을 내부 로그에 기록한다.

- Agent 2 route
- 선택된 persona ID와 version
- 모델과 프롬프트 version
- 토큰 사용량과 지연 시간
- 검색 근거 ID
- 만족도
- 자산화 및 동의 상태

---

## 18. 남은 비차단 정책

다음 항목은 기본 백엔드 개발을 시작한 뒤 확정해도 된다.

1. Q&A 이미지 최대 개수와 파일 크기
2. 페르소나 답변 재생성 허용 여부 및 최대 횟수
3. 페르소나 LLM timeout·재시도 횟수
4. 자산화 품질 통과 기준
5. 안전성 검사 실패 항목의 관리자 검토 여부
6. 재사용 동의 철회 후 백업 데이터의 삭제 유예 기간

---

## 19. 변경 이력

| 버전 | 날짜 | 변경 내용 |
| --- | --- | --- |
| v1.0-draft | 2026-07-24 | 실제 사람 멘토 계정·질문함·답변 구조로 작성 |
| v1.1-draft | 2026-07-25 | 멘티 전용 로그인, AI 페르소나 추천·답변·자산화 구조로 전환 |
