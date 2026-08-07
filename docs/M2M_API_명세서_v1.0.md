# M2M API 명세서 v1.0

## 문서 정보

| 항목 | 내용 |
| --- | --- |
| 서비스명 | M2M (Mentor to Mentee) |
| 문서 버전 | v1.0-draft |
| 작성일 | 2026-07-24 |
| API 버전 | v1 |
| 개발 Base URL | `http://localhost:8000/api/v1` |
| 운영 Base URL | `https://{service-domain}/api/v1` |
| 프로토콜 | 개발 HTTP / 운영 HTTPS |
| 인증 | Bearer Access Token |
| 자동 문서 | `http://localhost:8000/docs` (Swagger UI) |
| 대체 문서 | `http://localhost:8000/redoc` (ReDoc) |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |

---

## 1. 범위와 전제

### 1.1 포함 기능

- 멘티 회원가입·로그인
- 멘티 프로필·경험 관리
- AI 멀티턴 상담
- 정제 질문 확인 및 수정
- AI 답변 또는 멘토 연결 분기
- 지난 상담 목록 및 상세 조회
- 멘토 Top 3 추천·선택
- 멘토 질문함 및 답변 작성
- LLM을 통한 멘토 답변 정제 후 멘티 전달
- 답변 만족도 평가
- 답변 재사용 동의
- Q&A 목록·검색·상세·작성·댓글

### 1.2 사용자와 권한

| 역할 | 공개 가입 | 인증 | 주요 권한 |
| --- | --- | --- | --- |
| 멘티 `mentee` | 가능 | 이메일·비밀번호 로그인 | 상담, 멘토 선택, 답변 조회, 평가, Q&A |
| 멘토 `mentor` | 불가능 | 관리자가 발급한 계정으로 로그인 | 배정 질문 조회, 답변 작성, 재사용 동의 |
| 관리자 `admin` | 불가능 | 내부 계정 | 멘토 등록·계정 발급·활성 상태 관리 |

> 멘토 공개 회원가입 API는 제공하지 않는다. 멘토 질문함을 사용하려면 관리자가 멘토 정보와 로그인 계정을 사전에 생성해야 한다.

### 1.3 핵심 사용자 흐름

```text
멘티 회원가입·로그인
  → 자유 질문 입력
  → AI 추가 질문 및 멘티 답변 반복
  → AI가 정제 질문 생성
  → 멘티가 정제 질문 확인 또는 수정
  → 검색·검증·자기평가 실행
     ├─ 근거가 충분함: AI 답변 전달
     └─ 멘토가 필요함: 멘토 Top 3 추천
          → 멘티가 멘토 1명 선택
          → 멘토 질문함에 정제 질문 전달
          → 멘토 답변 작성
          → LLM이 개인정보 제거·구조화·가독성 보정
          → 최종 답변을 멘티에게 전달
          → 만족도 및 재사용 동의 수집
```

### 1.4 상담 세션 상태

| 상태 | 설명 | 다음 가능한 상태 |
| --- | --- | --- |
| `collecting_context` | AI가 추가 정보를 수집하는 중 | `awaiting_confirmation` |
| `awaiting_confirmation` | 정제 질문에 대한 멘티 확인 대기 | `collecting_context`, `analyzing` |
| `analyzing` | 검색·검증·자기평가 실행 중 | `ai_answered`, `mentor_recommended`, `failed` |
| `ai_answered` | AI 답변 제공 완료 | `completed` |
| `mentor_recommended` | 멘토 Top 3 추천 완료 | `mentor_selected` |
| `mentor_selected` | 멘티가 멘토를 선택함 | `waiting_mentor_answer` |
| `waiting_mentor_answer` | 선택된 멘토의 답변 대기 | `mentor_answer_processing`, `cancelled` |
| `mentor_answer_processing` | LLM이 멘토 답변을 정제하는 중 | `mentor_answered`, `failed` |
| `mentor_answered` | 멘티에게 멘토 답변 전달 완료 | `completed` |
| `completed` | 평가 또는 명시적 완료 처리된 세션 | 없음 |
| `cancelled` | 사용자가 종료한 세션 | 없음 |
| `failed` | AI 또는 외부 서비스 처리 실패 | 이전 처리 상태로 재시도 |

운영 규칙:

- 한 멘티가 동시에 유지할 수 있는 미완료 상담은 최대 3개다.
- `completed`, `cancelled` 세션은 활성 상담 수에 포함하지 않는다.
- 멘티는 자신이 생성한 상담만 조회할 수 있다.
- 멘토는 자신에게 배정된 질문만 조회하고 답변할 수 있다.

---

## 2. 공통 규칙

### 2.1 요청 헤더

인증이 필요한 API:

```http
Authorization: Bearer {accessToken}
Content-Type: application/json
X-Request-Id: {optional-client-request-id}
```

파일 업로드 API:

```http
Authorization: Bearer {accessToken}
Content-Type: multipart/form-data
```

### 2.2 성공 응답

```json
{
  "success": true,
  "data": {},
  "message": "처리되었습니다.",
  "requestId": "req_01K0ABCD1234"
}
```

`message`는 필요한 경우에만 포함한다.

### 2.3 오류 응답

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력값을 확인해주세요.",
    "details": [
      {
        "field": "password",
        "reason": "비밀번호는 8자 이상이어야 합니다."
      }
    ]
  },
  "requestId": "req_01K0ABCD1234"
}
```

운영 환경에서는 스택 트레이스, 프롬프트, API 키, 내부 DB 정보를 응답에 포함하지 않는다.

### 2.4 식별자

- 외부에 노출되는 식별자는 UUID 또는 UUID 기반 불투명 문자열을 사용한다.
- 예시: `ses_550e8400-e29b-41d4-a716-446655440000`
- 순차 증가 정수 ID는 외부 API에 노출하지 않는다.

### 2.5 날짜와 시간

- ISO 8601 UTC 형식 사용
- 예: `2026-07-24T08:30:00Z`
- 서버는 UTC로 저장하고 프론트엔드가 사용자 지역 시간으로 변환한다.

### 2.6 페이지네이션

요청:

```text
?page=1&limit=20
```

응답:

```json
{
  "items": [],
  "pagination": {
    "currentPage": 1,
    "totalPages": 3,
    "totalItems": 42,
    "hasNext": true,
    "hasPrev": false
  }
}
```

| 파라미터 | 타입 | 기본값 | 제약 |
| --- | --- | --- | --- |
| `page` | integer | 1 | 1 이상 |
| `limit` | integer | 20 | 1~100 |

### 2.7 AI 작업 처리 방식

검색·LLM·멘토 답변 정제처럼 오래 걸릴 수 있는 처리는 `202 Accepted`를 반환한다.

```json
{
  "success": true,
  "data": {
    "jobId": "job_550e8400-e29b-41d4-a716-446655440000",
    "status": "queued",
    "pollingUrl": "/api/v1/jobs/job_550e8400-e29b-41d4-a716-446655440000"
  }
}
```

프론트엔드는 1~2초 간격으로 작업 상태 API를 조회한다. 동일 작업에 대한 중복 실행을 막기 위해 생성·확정·분석 요청에서 `Idempotency-Key` 헤더 사용을 권장한다.

---

## 3. 엔드포인트 요약

### 3.1 인증

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| POST | `/auth/signup` | 없음 | 멘티 회원가입 |
| POST | `/auth/login` | 없음 | 멘티·멘토 로그인 |
| POST | `/auth/refresh` | Refresh Token | Access Token 갱신 |
| POST | `/auth/logout` | 필요 | 로그아웃 |
| GET | `/auth/me` | 필요 | 현재 사용자 조회 |

### 3.2 멘티 프로필·경험

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| GET | `/mentees/me` | 멘티 | 내 프로필 조회 |
| PATCH | `/mentees/me` | 멘티 | 내 프로필 수정 |
| POST | `/mentees/me/resume` | 멘티 | 이력서·경력기술서 업로드 |
| POST | `/mentees/me/portfolio` | 멘티 | 포트폴리오 파일 업로드 |
| GET | `/mentees/me/experiences` | 멘티 | 경험 목록 조회 |
| POST | `/mentees/me/experiences` | 멘티 | 경험 등록 |
| PATCH | `/mentees/me/experiences/{experienceId}` | 멘티 | 경험 수정 |
| DELETE | `/mentees/me/experiences/{experienceId}` | 멘티 | 경험 삭제 |

### 3.3 AI 상담·지난 상담

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| POST | `/consultations` | 멘티 | 상담 세션 생성 |
| GET | `/consultations` | 멘티 | 지난 상담 목록 |
| GET | `/consultations/{sessionId}` | 멘티 | 상담 상세 |
| POST | `/consultations/{sessionId}/messages` | 멘티 | 멀티턴 메시지 전송 |
| PATCH | `/consultations/{sessionId}/refined-question` | 멘티 | 정제 질문 직접 수정 |
| POST | `/consultations/{sessionId}/confirm` | 멘티 | 정제 질문 확정·분석 시작 |
| GET | `/consultations/{sessionId}/result` | 멘티 | AI 분석 결과 조회 |
| POST | `/consultations/{sessionId}/complete` | 멘티 | 상담 완료 |
| DELETE | `/consultations/{sessionId}` | 멘티 | 진행 중 상담 취소 |

### 3.4 멘토 추천·선택

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| GET | `/consultations/{sessionId}/mentor-recommendations` | 멘티 | 멘토 Top 3 조회 |
| POST | `/consultations/{sessionId}/mentor-selection` | 멘티 | 멘토 선택 및 질문 전달 |

### 3.5 멘토 질문함·답변

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| GET | `/mentor/questions` | 멘토 | 배정 질문 목록 |
| GET | `/mentor/questions/{assignmentId}` | 멘토 | 배정 질문 상세 |
| POST | `/mentor/questions/{assignmentId}/accept` | 멘토 | 질문 수락 |
| POST | `/mentor/questions/{assignmentId}/decline` | 멘토 | 질문 거절 |
| POST | `/mentor/questions/{assignmentId}/answers` | 멘토 | 답변 제출 |
| GET | `/mentor/questions/{assignmentId}/answers/{answerId}` | 멘토 | 제출 답변 상태 조회 |

### 3.6 평가·재사용 동의

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| POST | `/consultations/{sessionId}/feedback` | 멘티 | 만족도 평가 |
| PUT | `/consultations/{sessionId}/reuse-consent` | 멘티 | 멘티 재사용 동의 설정 |
| PUT | `/mentor/answers/{answerId}/reuse-consent` | 멘토 | 멘토 재사용 동의 설정 |

### 3.7 Q&A

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| GET | `/qna/posts` | 선택 | Q&A 목록·검색 |
| POST | `/qna/posts` | 멘티 | Q&A 글 작성 |
| GET | `/qna/posts/{postId}` | 선택 | Q&A 상세·댓글·연관 글 |
| PATCH | `/qna/posts/{postId}` | 작성자 | Q&A 글 수정 |
| DELETE | `/qna/posts/{postId}` | 작성자 | Q&A 글 삭제 |
| POST | `/qna/images` | 로그인 | Q&A 이미지 업로드 |
| POST | `/qna/posts/{postId}/comments` | 로그인 | 댓글 작성 |
| PATCH | `/qna/posts/{postId}/comments/{commentId}` | 작성자 | 댓글 수정 |
| DELETE | `/qna/posts/{postId}/comments/{commentId}` | 작성자 | 댓글 삭제 |

### 3.8 관리자용 멘토 등록

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| GET | `/admin/mentors` | 관리자 | 멘토 목록·상태 조회 |
| POST | `/admin/mentors` | 관리자 | 멘토 프로필·로그인 계정 생성 |
| PATCH | `/admin/mentors/{mentorId}` | 관리자 | 멘토 정보·활성 상태 수정 |
| POST | `/admin/mentors/{mentorId}/invite` | 관리자 | 최초 로그인 초대 재발송 |

### 3.9 공통 작업

| Method | Endpoint | 인증 | 설명 |
| --- | --- | --- | --- |
| GET | `/jobs/{jobId}` | 필요 | 비동기 작업 상태 조회 |
| POST | `/jobs/{jobId}/retry` | 소유자 | 실패 작업 재시도 |

---

## 4. 인증 API

### 4.1 멘티 회원가입

**Endpoint**: `POST /auth/signup`  
**인증 필요**: 없음

#### Request

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

| 필드 | 타입 | 필수 | 설명 | 제약 |
| --- | --- | --- | --- | --- |
| `email` | string | 예 | 이메일 | 최대 255자, 이메일 형식 |
| `password` | string | 예 | 비밀번호 | 8~72자 |
| `name` | string | 예 | 이름 또는 닉네임 | 2~50자 |
| `currentStatus` | enum | 예 | 현재 상태 | `student`, `job_seeker`, `career_change`, `employed`, `other` |
| `termsConsent` | boolean | 예 | 이용약관 동의 | `true` 필수 |
| `privacyConsent` | boolean | 예 | 개인정보 수집 동의 | `true` 필수 |

#### Response: 201 Created

```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_550e8400-e29b-41d4-a716-446655440000",
      "role": "mentee",
      "email": "mentee@example.com",
      "name": "김멘티",
      "profileCompleted": false,
      "createdAt": "2026-07-24T08:30:00Z"
    },
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "expiresIn": 3600
  }
}
```

오류:

- `409 EMAIL_EXISTS`
- `400 TERMS_CONSENT_REQUIRED`
- `422 VALIDATION_ERROR`

### 4.2 로그인

**Endpoint**: `POST /auth/login`  
**인증 필요**: 없음

멘티와 관리자가 발급한 멘토 계정이 공통으로 사용한다.

#### Request

```json
{
  "email": "mentee@example.com",
  "password": "password123!"
}
```

#### Response: 200 OK

```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_550e8400-e29b-41d4-a716-446655440000",
      "role": "mentee",
      "email": "mentee@example.com",
      "name": "김멘티"
    },
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "expiresIn": 3600
  }
}
```

오류:

- `401 INVALID_CREDENTIALS`
- `403 ACCOUNT_DISABLED`

### 4.3 토큰 갱신

**Endpoint**: `POST /auth/refresh`

```json
{
  "refreshToken": "eyJ..."
}
```

성공 시 새 Access Token을 반환한다. Refresh Token Rotation 적용을 권장한다.

### 4.4 로그아웃

**Endpoint**: `POST /auth/logout`  
**인증 필요**: 필요

현재 Refresh Token을 폐기한다.

### 4.5 내 정보 조회

**Endpoint**: `GET /auth/me`  
**인증 필요**: 필요

```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_550e8400-e29b-41d4-a716-446655440000",
      "role": "mentee",
      "email": "mentee@example.com",
      "name": "김멘티",
      "profileCompleted": true
    }
  }
}
```

---

## 5. 멘티 프로필·경험 API

### 5.1 내 프로필 조회

**Endpoint**: `GET /mentees/me`  
**인증 필요**: 멘티

#### Response: 200 OK

```json
{
  "success": true,
  "data": {
    "mentee": {
      "id": "mte_550e8400-e29b-41d4-a716-446655440000",
      "name": "김멘티",
      "currentStatus": "student",
      "background": {
        "school": "M2M대학교",
        "major": "경영학",
        "grade": "4학년",
        "enrollmentStatus": "enrolled"
      },
      "consideringOptions": ["internship", "full_time"],
      "targetRoles": ["데이터 분석가"],
      "interestDomains": ["IT", "금융"],
      "resumeUrl": null,
      "portfolioUrl": null,
      "activeSessionCount": 1,
      "activeSessionLimit": 3,
      "updatedAt": "2026-07-24T08:30:00Z"
    }
  }
}
```

### 5.2 내 프로필 수정

**Endpoint**: `PATCH /mentees/me`  
**인증 필요**: 멘티

전달한 필드만 수정한다.

```json
{
  "currentStatus": "job_seeker",
  "background": {
    "school": "M2M대학교",
    "major": "경영학",
    "grade": "졸업",
    "enrollmentStatus": "graduated"
  },
  "consideringOptions": ["full_time"],
  "targetRoles": ["데이터 분석가", "데이터 기획자"],
  "interestDomains": ["IT", "금융"],
  "portfolioUrl": "https://portfolio.example.com"
}
```

### 5.3 이력서·경력기술서 업로드

**Endpoint**: `POST /mentees/me/resume`  
**Content-Type**: `multipart/form-data`

| 필드 | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `file` | file | 예 | PDF, DOCX, 최대 10MB |
| `extractExperiences` | boolean | 아니오 | 기본값 `true` |

#### Response: 202 Accepted

```json
{
  "success": true,
  "data": {
    "jobId": "job_550e8400-e29b-41d4-a716-446655440000",
    "status": "queued",
    "fileName": "resume.pdf"
  }
}
```

문서 원문은 비공개 저장소에 저장하고 LLM 전송 전 개인정보를 최소화한다.

### 5.4 포트폴리오 업로드

**Endpoint**: `POST /mentees/me/portfolio`  
**Content-Type**: `multipart/form-data`

| 필드 | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `file` | file | 예 | PDF, PPTX, 최대 20MB |
| `extractExperiences` | boolean | 아니오 | 기본값 `true` |

회원가입 화면에서 이력서·경력기술서와 포트폴리오를 받더라도 API 호출은 다음 순서로 처리한다.

```text
POST /auth/signup
  → Access Token 발급
  → POST /mentees/me/resume
  → POST /mentees/me/portfolio
```

파일 업로드가 실패해도 생성된 계정은 유지하며 마이페이지에서 다시 업로드할 수 있다.

### 5.5 경험 목록 조회

**Endpoint**: `GET /mentees/me/experiences`

### 5.6 경험 등록

**Endpoint**: `POST /mentees/me/experiences`

```json
{
  "experienceType": "project",
  "title": "고객 이탈 예측 프로젝트",
  "description": "고객 행동 데이터를 분석해 이탈 가능성을 예측했습니다.",
  "organization": "교내 데이터 동아리",
  "startDate": "2025-03",
  "endDate": "2025-06",
  "role": "데이터 분석",
  "keySkills": ["문제 정의", "데이터 시각화"],
  "tools": ["Python", "Pandas", "Tableau"]
}
```

`experienceType` 허용값:

- `project`
- `internship`
- `work`
- `club`
- `course`
- `certification`
- `award`
- `education`
- `etc`

### 5.7 경험 수정·삭제

- `PATCH /mentees/me/experiences/{experienceId}`
- `DELETE /mentees/me/experiences/{experienceId}`

본인 경험만 수정·삭제할 수 있다.

---

## 6. AI 상담 API

### 6.1 상담 세션 생성

**Endpoint**: `POST /consultations`  
**인증 필요**: 멘티

#### Request

```json
{
  "initialMessage": "비전공자인데 데이터 분석가로 취업하려면 무엇부터 준비해야 하나요?"
}
```

| 필드 | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `initialMessage` | string | 예 | 10~3000자 |

#### Response: 201 Created

```json
{
  "success": true,
  "data": {
    "session": {
      "id": "ses_550e8400-e29b-41d4-a716-446655440000",
      "title": "비전공자의 데이터 분석가 취업 준비",
      "status": "collecting_context",
      "createdAt": "2026-07-24T08:30:00Z"
    },
    "assistantMessage": {
      "id": "msg_550e8400-e29b-41d4-a716-446655440000",
      "role": "assistant",
      "content": "현재 전공과 데이터 분석 관련 경험을 알려주세요.",
      "createdAt": "2026-07-24T08:30:02Z"
    }
  }
}
```

오류:

- `409 ACTIVE_SESSION_LIMIT_EXCEEDED`
- `422 VALIDATION_ERROR`
- `429 RATE_LIMIT_EXCEEDED`
- `503 AI_SERVICE_UNAVAILABLE`

### 6.2 상담 메시지 전송

**Endpoint**: `POST /consultations/{sessionId}/messages`  
**인증 필요**: 멘티

#### Request

```json
{
  "content": "경영학과 4학년이고, Python 기초 수업과 매출 데이터 분석 프로젝트를 해봤어요."
}
```

#### Response: 200 OK — 추가 정보가 더 필요한 경우

```json
{
  "success": true,
  "data": {
    "userMessage": {
      "id": "msg_user_001",
      "role": "user",
      "content": "경영학과 4학년이고, Python 기초 수업과 매출 데이터 분석 프로젝트를 해봤어요.",
      "createdAt": "2026-07-24T08:32:00Z"
    },
    "assistantMessage": {
      "id": "msg_ai_002",
      "role": "assistant",
      "content": "취업 목표 시점과 가장 어려움을 느끼는 부분은 무엇인가요?",
      "createdAt": "2026-07-24T08:32:02Z"
    },
    "sessionStatus": "collecting_context",
    "needMoreInfo": true,
    "missingFields": ["target_timeline", "current_bottleneck"]
  }
}
```

#### Response: 200 OK — 정제 질문이 완성된 경우

```json
{
  "success": true,
  "data": {
    "assistantMessage": {
      "id": "msg_ai_003",
      "role": "assistant",
      "content": "질문을 아래와 같이 정리했어요. 내용을 확인해주세요.",
      "createdAt": "2026-07-24T08:35:00Z"
    },
    "sessionStatus": "awaiting_confirmation",
    "needMoreInfo": false,
    "refinedQuestion": {
      "content": "경영학과 4학년으로 Python 기초와 매출 데이터 분석 프로젝트 경험이 있습니다. 6개월 이내 데이터 분석가 취업을 목표로 할 때 포트폴리오와 기술 역량을 어떤 순서로 보완해야 할까요?",
      "conversationSummary": "경영학 전공, Python 기초, 매출 분석 프로젝트 경험 보유. 6개월 이내 취업 희망.",
      "currentBottleneck": "취업 준비 우선순위 설정",
      "expectedAnswerType": "단계별 준비 계획"
    }
  }
}
```

### 6.3 정제 질문 수정

**Endpoint**: `PATCH /consultations/{sessionId}/refined-question`

```json
{
  "content": "경영학과 4학년으로 데이터 분석가 취업을 준비하고 있습니다. 금융 데이터 분석 직무를 목표로 할 때 6개월 동안 어떤 포트폴리오와 기술을 준비해야 할까요?"
}
```

세션 상태가 `awaiting_confirmation`일 때만 수정할 수 있다.

### 6.4 정제 질문 확정 및 분석 시작

**Endpoint**: `POST /consultations/{sessionId}/confirm`  
**권장 헤더**: `Idempotency-Key: {uuid}`

#### Request

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
    "jobId": "job_550e8400-e29b-41d4-a716-446655440000",
    "sessionId": "ses_550e8400-e29b-41d4-a716-446655440000",
    "sessionStatus": "analyzing",
    "jobStatus": "queued",
    "pollingUrl": "/api/v1/jobs/job_550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 6.5 분석 결과 조회

**Endpoint**: `GET /consultations/{sessionId}/result`

#### AI 답변 결과: 200 OK

```json
{
  "success": true,
  "data": {
    "sessionId": "ses_550e8400-e29b-41d4-a716-446655440000",
    "status": "ai_answered",
    "resultType": "ai_answer",
    "answer": {
      "content": "첫 2개월은 SQL과 통계 기초를 보완하고...",
      "confidenceScore": 0.84,
      "reason": "유사한 멘토 답변과 직무 준비 자료에서 충분한 근거를 확인했습니다.",
      "recommendedNextAction": "금융 데이터를 활용한 분석 프로젝트 1개를 완성해보세요.",
      "sources": [
        {
          "sourceId": "ans_001",
          "sourceType": "mentor_answer",
          "title": "비전공자의 데이터 분석가 준비",
          "whyUsed": "유사한 배경과 목표를 가진 사례"
        }
      ]
    }
  }
}
```

#### 멘토 추천 결과: 200 OK

```json
{
  "success": true,
  "data": {
    "sessionId": "ses_550e8400-e29b-41d4-a716-446655440000",
    "status": "mentor_recommended",
    "resultType": "mentor_recommendation",
    "reason": "개인 경력 전환 상황에 대한 구체적인 판단이 필요합니다.",
    "recommendationUrl": "/api/v1/consultations/ses_550e8400-e29b-41d4-a716-446655440000/mentor-recommendations"
  }
}
```

### 6.6 지난 상담 목록

**Endpoint**: `GET /consultations`

Query:

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `status` | string | 상태 필터, 생략 시 전체 |
| `resultType` | string | `ai_answer`, `mentor_answer` |
| `query` | string | 제목·정제 질문 검색 |
| `page` | integer | 페이지 |
| `limit` | integer | 페이지 크기 |

#### Response: 200 OK

```json
{
  "success": true,
  "data": {
    "consultations": [
      {
        "id": "ses_001",
        "title": "비전공자의 데이터 분석가 취업 준비",
        "refinedQuestion": "금융 데이터 분석 직무를 목표로 할 때...",
        "status": "mentor_answered",
        "resultType": "mentor_answer",
        "mentor": {
          "id": "mtr_001",
          "displayName": "김OO 멘토",
          "currentRole": "핀테크 데이터 분석가"
        },
        "updatedAt": "2026-07-24T10:30:00Z"
      }
    ],
    "pagination": {
      "currentPage": 1,
      "totalPages": 1,
      "totalItems": 1,
      "hasNext": false,
      "hasPrev": false
    }
  }
}
```

### 6.7 상담 상세

**Endpoint**: `GET /consultations/{sessionId}`

메시지 이력, 정제 질문, 분석 결과, 선택 멘토, 최종 답변, 평가를 한 번에 반환한다.

### 6.8 상담 완료·취소

- `POST /consultations/{sessionId}/complete`
- `DELETE /consultations/{sessionId}`

멘토 답변을 기다리는 세션 취소 시 이미 전달된 질문의 처리 정책을 함께 적용해야 한다.

---

## 7. 멘토 추천·선택 API

### 7.1 멘토 Top 3 조회

**Endpoint**: `GET /consultations/{sessionId}/mentor-recommendations`

세션 상태가 `mentor_recommended`일 때 조회할 수 있다.

#### Response: 200 OK

```json
{
  "success": true,
  "data": {
    "sessionId": "ses_001",
    "mentors": [
      {
        "rank": 1,
        "mentorId": "mtr_001",
        "displayName": "김OO",
        "currentRole": "핀테크 데이터 분석가",
        "yearsOfExperience": 6,
        "expertise": ["데이터 분석", "비전공자 전환", "금융"],
        "profileSummary": "경영학 전공 후 데이터 분석가로 전환한 경험이 있습니다.",
        "recommendationReason": "멘티와 유사한 비전공 전환 경험과 금융 데이터 실무 경험을 보유하고 있습니다.",
        "matchScore": 0.91,
        "averageRating": 4.8,
        "expectedResponseDays": 3
      }
    ],
    "expiresAt": "2026-07-25T08:30:00Z"
  }
}
```

민감 정보는 노출하지 않으며 이름은 서비스 정책에 따라 마스킹할 수 있다.

### 7.2 멘토 선택

**Endpoint**: `POST /consultations/{sessionId}/mentor-selection`  
**권장 헤더**: `Idempotency-Key: {uuid}`

```json
{
  "mentorId": "mtr_001"
}
```

#### Response: 201 Created

```json
{
  "success": true,
  "data": {
    "assignment": {
      "id": "asg_001",
      "sessionId": "ses_001",
      "mentorId": "mtr_001",
      "status": "pending",
      "question": "경영학과 4학년으로...",
      "assignedAt": "2026-07-24T09:00:00Z",
      "answerDueAt": "2026-07-27T09:00:00Z"
    }
  },
  "message": "선택한 멘토에게 질문을 전달했습니다."
}
```

오류:

- `409 MENTOR_ALREADY_SELECTED`
- `409 RECOMMENDATION_EXPIRED`
- `409 MENTOR_UNAVAILABLE`

---

## 8. 멘토 질문함·답변 API

### 8.0 관리자 멘토 등록

**Endpoint**: `POST /admin/mentors`  
**인증 필요**: 관리자

공개 회원가입 대신 관리자가 멘토 프로필과 로그인 계정을 생성한다.

```json
{
  "email": "mentor@example.com",
  "name": "김멘토",
  "currentRole": "핀테크 데이터 분석가",
  "yearsOfExperience": 6,
  "expertise": ["데이터 분석", "비전공자 전환", "금융"],
  "profileSummary": "경영학 전공 후 데이터 분석가로 전환한 경험이 있습니다.",
  "weeklyQuestionLimit": 7,
  "active": true,
  "sendInvite": true
}
```

#### Response: 201 Created

```json
{
  "success": true,
  "data": {
    "mentor": {
      "id": "mtr_001",
      "email": "mentor@example.com",
      "name": "김멘토",
      "active": true,
      "accountStatus": "invited",
      "createdAt": "2026-07-24T08:30:00Z"
    }
  },
  "message": "멘토 계정을 생성하고 최초 로그인 초대를 발송했습니다."
}
```

초대 링크는 일회용이며 만료 시간을 둔다. 멘토는 링크에서 비밀번호를 설정한 후 공통 로그인 API를 사용한다.

### 8.1 멘토 질문 목록

**Endpoint**: `GET /mentor/questions`  
**인증 필요**: 멘토

Query:

- `status`: `pending`, `accepted`, `answered`, `declined`, `expired`
- `page`, `limit`

#### Response: 200 OK

```json
{
  "success": true,
  "data": {
    "questions": [
      {
        "assignmentId": "asg_001",
        "title": "비전공자의 금융 데이터 분석가 준비",
        "questionPreview": "경영학과 4학년으로...",
        "status": "pending",
        "assignedAt": "2026-07-24T09:00:00Z",
        "answerDueAt": "2026-07-27T09:00:00Z",
        "isUrgent": false
      }
    ],
    "pagination": {
      "currentPage": 1,
      "totalPages": 1,
      "totalItems": 1,
      "hasNext": false,
      "hasPrev": false
    }
  }
}
```

### 8.2 멘토 질문 상세

**Endpoint**: `GET /mentor/questions/{assignmentId}`

#### Response: 200 OK

```json
{
  "success": true,
  "data": {
    "assignment": {
      "id": "asg_001",
      "status": "accepted",
      "question": "경영학과 4학년으로 금융 데이터 분석가를...",
      "context": {
        "currentStatus": "student",
        "backgroundSummary": "경영학 전공, Python 기초 수강",
        "experienceSummary": "매출 데이터 분석 프로젝트 경험",
        "targetRole": "금융 데이터 분석가",
        "currentBottleneck": "준비 우선순위 설정",
        "expectedAnswerType": "6개월 단계별 계획"
      },
      "assignedAt": "2026-07-24T09:00:00Z",
      "answerDueAt": "2026-07-27T09:00:00Z"
    }
  }
}
```

멘티의 이름, 이메일, 연락처, 원문 이력서는 멘토에게 제공하지 않는다.

### 8.3 질문 수락

**Endpoint**: `POST /mentor/questions/{assignmentId}/accept`

#### Response: 200 OK

```json
{
  "success": true,
  "data": {
    "assignmentId": "asg_001",
    "status": "accepted",
    "acceptedAt": "2026-07-24T09:10:00Z"
  }
}
```

### 8.4 질문 거절

**Endpoint**: `POST /mentor/questions/{assignmentId}/decline`

```json
{
  "reasonCode": "OUT_OF_EXPERTISE",
  "reasonDetail": "현재 질문은 제 전문 분야와 거리가 있습니다."
}
```

`reasonCode`:

- `OUT_OF_EXPERTISE`
- `NO_CAPACITY`
- `CONFLICT_OF_INTEREST`
- `OTHER`

거절 후 시스템은 차순위 추천 멘토 재선택을 멘티에게 안내한다.

### 8.5 멘토 답변 제출

**Endpoint**: `POST /mentor/questions/{assignmentId}/answers`  
**인증 필요**: 멘토

```json
{
  "content": "저도 경영학과에서 데이터 분석 직무로 전환했습니다. 우선 SQL을...",
  "reuseConsent": true
}
```

| 필드 | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `content` | string | 예 | 50~10000자 |
| `reuseConsent` | boolean | 예 | 익명·구조화 후 재사용 동의 |

#### Response: 202 Accepted

```json
{
  "success": true,
  "data": {
    "answerId": "ans_001",
    "jobId": "job_002",
    "status": "processing",
    "processingSteps": [
      "privacy_check",
      "structure_refinement",
      "grounding_check",
      "delivery"
    ]
  },
  "message": "답변을 제출했습니다. 검수 후 멘티에게 전달됩니다."
}
```

LLM 처리 원칙:

- 멘토의 핵심 의미와 조언을 변경하지 않는다.
- 맞춤법·문단 구조·가독성을 개선할 수 있다.
- 불필요한 개인정보와 제3자 식별 정보를 제거한다.
- 확정적 채용 보장, 차별적 표현, 위험한 조언을 표시하거나 차단한다.
- 원문과 최종 전달본을 별도로 저장한다.
- 자동 검수 실패 시 멘티에게 전달하지 않고 관리자 검토 상태로 전환한다.

### 8.6 멘토 답변 상태 조회

**Endpoint**: `GET /mentor/questions/{assignmentId}/answers/{answerId}`

```json
{
  "success": true,
  "data": {
    "answerId": "ans_001",
    "status": "delivered",
    "submittedAt": "2026-07-24T10:00:00Z",
    "deliveredAt": "2026-07-24T10:01:30Z",
    "reuseConsent": true
  }
}
```

---

## 9. 멘토 답변 전달·평가·재사용 동의

### 9.1 멘티가 받는 최종 멘토 답변

`GET /consultations/{sessionId}` 또는 결과 API에서 다음 형식으로 제공한다.

```json
{
  "resultType": "mentor_answer",
  "mentorAnswer": {
    "answerId": "ans_001",
    "mentor": {
      "displayName": "김OO 멘토",
      "currentRole": "핀테크 데이터 분석가"
    },
    "content": "저 역시 비전공자로 전환했습니다. 다음 순서로 준비해보세요...",
    "summary": "SQL·통계 기초 → 금융 데이터 프로젝트 → 포트폴리오 개선",
    "deliveredAt": "2026-07-24T10:01:30Z"
  },
  "feedbackSubmitted": false,
  "reuseConsent": null
}
```

### 9.2 만족도 평가

**Endpoint**: `POST /consultations/{sessionId}/feedback`

```json
{
  "answerId": "ans_001",
  "rating": 5,
  "helpfulTags": ["specific", "actionable", "empathetic"],
  "comment": "준비 순서가 구체적이라 도움이 됐어요."
}
```

| 필드 | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `answerId` | string | 예 | 해당 세션 답변 |
| `rating` | integer | 예 | 1~5 |
| `helpfulTags` | array | 아니오 | 허용 태그 목록 |
| `comment` | string | 아니오 | 최대 1000자 |

한 답변당 한 번 평가할 수 있으며 수정 정책이 필요하면 `PUT` API를 추가한다.

### 9.3 멘티 재사용 동의

**Endpoint**: `PUT /consultations/{sessionId}/reuse-consent`

```json
{
  "answerId": "ans_001",
  "consent": true,
  "scope": "anonymized_rag"
}
```

### 9.4 멘토 재사용 동의

**Endpoint**: `PUT /mentor/answers/{answerId}/reuse-consent`

```json
{
  "consent": true,
  "scope": "anonymized_rag"
}
```

자산화 조건:

```text
멘티 동의 == true
AND 멘토 동의 == true
AND 개인정보 검사 통과
AND 품질 검사 통과
```

동의 철회 시 신규 검색 대상에서 제외하며, 법적 보관 의무가 없는 파생 데이터 삭제 정책을 적용한다.

---

## 10. Q&A API

### 10.1 Q&A 목록 및 검색

**Endpoint**: `GET /qna/posts`  
**인증 필요**: 선택

Query:

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `query` | string | 제목·본문 검색 |
| `category` | string | 카테고리 |
| `sort` | string | `latest`, `popular`, `unanswered` |
| `page` | integer | 페이지 |
| `limit` | integer | 페이지 크기 |

#### Response: 200 OK

```json
{
  "success": true,
  "data": {
    "posts": [
      {
        "id": "qna_001",
        "category": "직무·취업",
        "title": "비전공자인데 PM 준비하려면 무엇부터 해야 하나요?",
        "preview": "현재 경영학과 재학 중이고...",
        "thumbnailUrl": "https://cdn.example.com/qna/qna_001.jpg",
        "author": {
          "displayName": "취준생A",
          "profileImageUrl": null
        },
        "commentCount": 3,
        "viewCount": 128,
        "isAnswered": true,
        "createdAt": "2026-07-23T08:00:00Z"
      }
    ],
    "pagination": {
      "currentPage": 1,
      "totalPages": 5,
      "totalItems": 93,
      "hasNext": true,
      "hasPrev": false
    }
  }
}
```

### 10.2 Q&A 글 작성

**Endpoint**: `POST /qna/posts`  
**인증 필요**: 멘티

```json
{
  "category": "직무·취업",
  "title": "비전공자인데 PM 준비하려면 무엇부터 해야 하나요?",
  "content": "현재 경영학과 재학 중이며...",
  "imageIds": ["img_001"],
  "anonymous": false
}
```

| 필드 | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `category` | string | 예 | 서버 허용 카테고리 |
| `title` | string | 예 | 5~120자 |
| `content` | string | 예 | 20~10000자 |
| `imageIds` | array | 아니오 | 최대 5개 |
| `anonymous` | boolean | 아니오 | 기본값 `false` |

### 10.3 Q&A 상세

**Endpoint**: `GET /qna/posts/{postId}`

#### Response: 200 OK

```json
{
  "success": true,
  "data": {
    "post": {
      "id": "qna_001",
      "category": "직무·취업",
      "title": "비전공자인데 PM 준비하려면 무엇부터 해야 하나요?",
      "content": "현재 경영학과 재학 중이며...",
      "images": [
        {
          "id": "img_001",
          "url": "https://cdn.example.com/qna/qna_001.jpg"
        }
      ],
      "author": {
        "displayName": "취준생A",
        "profileImageUrl": null
      },
      "viewCount": 129,
      "commentCount": 3,
      "createdAt": "2026-07-23T08:00:00Z",
      "updatedAt": "2026-07-23T08:00:00Z",
      "canEdit": false,
      "canDelete": false
    },
    "comments": [
      {
        "id": "cmt_001",
        "author": {
          "displayName": "현직PM",
          "roleLabel": "멘토"
        },
        "content": "먼저 문제 정의와 사용자 인터뷰 경험을 만들어보세요.",
        "createdAt": "2026-07-23T09:00:00Z",
        "canEdit": false,
        "canDelete": false
      }
    ],
    "relatedPosts": [
      {
        "id": "qna_002",
        "title": "PM 포트폴리오는 어떻게 구성해야 하나요?",
        "thumbnailUrl": null,
        "commentCount": 2
      }
    ]
  }
}
```

### 10.4 Q&A 수정·삭제

- `PATCH /qna/posts/{postId}`
- `DELETE /qna/posts/{postId}`

작성자만 가능하며 삭제는 기본적으로 소프트 삭제한다.

### 10.5 Q&A 이미지 업로드

**Endpoint**: `POST /qna/images`  
**Content-Type**: `multipart/form-data`

| 필드 | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `file` | file | 예 | JPG, PNG, WEBP, 최대 5MB |

글 작성 전에 이미지를 업로드하고 반환받은 `imageId`를 `POST /qna/posts`의 `imageIds`에 전달한다. 게시글과 연결되지 않은 이미지는 일정 시간 후 삭제한다.

### 10.6 댓글 작성

**Endpoint**: `POST /qna/posts/{postId}/comments`

```json
{
  "content": "먼저 문제 정의와 사용자 인터뷰 경험을 만들어보세요.",
  "anonymous": false
}
```

### 10.7 댓글 수정·삭제

- `PATCH /qna/posts/{postId}/comments/{commentId}`
- `DELETE /qna/posts/{postId}/comments/{commentId}`

---

## 11. 비동기 작업 API

### 11.1 작업 상태 조회

**Endpoint**: `GET /jobs/{jobId}`

#### 처리 중

```json
{
  "success": true,
  "data": {
    "jobId": "job_001",
    "jobType": "consultation_analysis",
    "status": "processing",
    "progress": 60,
    "currentStep": "answer_verification",
    "createdAt": "2026-07-24T08:40:00Z",
    "updatedAt": "2026-07-24T08:40:05Z"
  }
}
```

#### 완료

```json
{
  "success": true,
  "data": {
    "jobId": "job_001",
    "status": "completed",
    "progress": 100,
    "resultUrl": "/api/v1/consultations/ses_001/result",
    "completedAt": "2026-07-24T08:40:10Z"
  }
}
```

#### 실패

```json
{
  "success": true,
  "data": {
    "jobId": "job_001",
    "status": "failed",
    "error": {
      "code": "AI_SERVICE_TIMEOUT",
      "message": "AI 응답 시간이 초과되었습니다.",
      "retryable": true
    }
  }
}
```

### 11.2 실패 작업 재시도

**Endpoint**: `POST /jobs/{jobId}/retry`

재시도 가능한 실패 작업만 허용한다.

---

## 12. 주요 오류 코드

### 12.1 인증·권한

| 코드 | HTTP | 설명 |
| --- | --- | --- |
| `UNAUTHORIZED` | 401 | 인증 필요 |
| `INVALID_CREDENTIALS` | 401 | 이메일 또는 비밀번호 불일치 |
| `TOKEN_EXPIRED` | 401 | Access Token 만료 |
| `INVALID_TOKEN` | 401 | 유효하지 않은 토큰 |
| `FORBIDDEN` | 403 | 권한 없음 |
| `ACCOUNT_DISABLED` | 403 | 비활성 계정 |
| `MENTOR_ACCOUNT_NOT_PROVISIONED` | 403 | 관리자가 발급하지 않은 멘토 계정 |

### 12.2 입력·파일

| 코드 | HTTP | 설명 |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | 입력값 검증 실패 |
| `INVALID_FILE_TYPE` | 400 | 허용되지 않은 파일 형식 |
| `FILE_TOO_LARGE` | 413 | 파일 크기 초과 |
| `TERMS_CONSENT_REQUIRED` | 400 | 필수 약관 미동의 |

### 12.3 상담

| 코드 | HTTP | 설명 |
| --- | --- | --- |
| `CONSULTATION_NOT_FOUND` | 404 | 상담 없음 |
| `INVALID_SESSION_STATE` | 409 | 현재 상태에서 요청 불가 |
| `ACTIVE_SESSION_LIMIT_EXCEEDED` | 409 | 활성 상담 3개 초과 |
| `REFINED_QUESTION_NOT_READY` | 409 | 정제 질문 미완성 |
| `ALREADY_CONFIRMED` | 409 | 이미 확정된 질문 |
| `MENTOR_ALREADY_SELECTED` | 409 | 이미 멘토 선택 완료 |
| `RECOMMENDATION_EXPIRED` | 409 | 추천 결과 만료 |
| `MENTOR_UNAVAILABLE` | 409 | 선택 멘토 응답 불가 |

### 12.4 멘토 답변·동의

| 코드 | HTTP | 설명 |
| --- | --- | --- |
| `ASSIGNMENT_NOT_FOUND` | 404 | 배정 질문 없음 |
| `ASSIGNMENT_EXPIRED` | 409 | 답변 기한 만료 |
| `ANSWER_ALREADY_SUBMITTED` | 409 | 이미 답변 제출 |
| `ANSWER_QUALITY_REVIEW_REQUIRED` | 409 | 관리자 검토 필요 |
| `FEEDBACK_ALREADY_SUBMITTED` | 409 | 이미 평가 제출 |
| `CONSENT_REQUIRED` | 400 | 동의값 필요 |

### 12.5 Q&A

| 코드 | HTTP | 설명 |
| --- | --- | --- |
| `QNA_POST_NOT_FOUND` | 404 | 게시글 없음 |
| `QNA_COMMENT_NOT_FOUND` | 404 | 댓글 없음 |
| `QNA_EDIT_FORBIDDEN` | 403 | 수정 권한 없음 |
| `QNA_DELETE_FORBIDDEN` | 403 | 삭제 권한 없음 |

### 12.6 AI·서버

| 코드 | HTTP | 설명 |
| --- | --- | --- |
| `RATE_LIMIT_EXCEEDED` | 429 | 호출 횟수 초과 |
| `AI_SERVICE_UNAVAILABLE` | 503 | AI 서비스 이용 불가 |
| `AI_SERVICE_TIMEOUT` | 504 | AI 응답 시간 초과 |
| `DATABASE_ERROR` | 500 | DB 처리 오류 |
| `INTERNAL_ERROR` | 500 | 서버 내부 오류 |

---

## 13. 프론트엔드 화면별 API 연결

### 13.1 로그인·회원가입

| 화면 기능 | API |
| --- | --- |
| 멘티 회원가입 | `POST /auth/signup` |
| 로그인 | `POST /auth/login` |
| 로그인 유지 | `POST /auth/refresh` |
| 사용자 이름 표시 | `GET /auth/me` |

### 13.2 메인 상담 화면

| 화면 기능 | API |
| --- | --- |
| 첫 질문 전송 | `POST /consultations` |
| AI 추가 질문 응답 | `POST /consultations/{sessionId}/messages` |
| 정제 질문 수정 | `PATCH /consultations/{sessionId}/refined-question` |
| 정제 질문 확인 | `POST /consultations/{sessionId}/confirm` |
| 로딩 상태 | `GET /jobs/{jobId}` |
| AI 결과 | `GET /consultations/{sessionId}/result` |
| 왼쪽 지난 상담 목록 | `GET /consultations` |

### 13.3 멘토 추천 카드

| 화면 기능 | API |
| --- | --- |
| Top 3 카드 표시 | `GET /consultations/{sessionId}/mentor-recommendations` |
| 멘토 선택 | `POST /consultations/{sessionId}/mentor-selection` |

### 13.4 멘토 질문함

| 화면 기능 | API |
| --- | --- |
| 질문 목록 | `GET /mentor/questions` |
| 질문 상세 | `GET /mentor/questions/{assignmentId}` |
| 수락·거절 | `POST .../accept`, `POST .../decline` |
| 답변 작성 | `POST .../answers` |
| 전달 상태 | `GET .../answers/{answerId}` |

### 13.5 Q&A

| 화면 기능 | API |
| --- | --- |
| 목록·검색·페이지 이동 | `GET /qna/posts` |
| 상세·댓글·연관 글 | `GET /qna/posts/{postId}` |
| 이미지 업로드 | `POST /qna/images` |
| 글 작성 | `POST /qna/posts` |
| 글 수정·삭제 | `PATCH`, `DELETE /qna/posts/{postId}` |
| 댓글 작성·수정·삭제 | `/qna/posts/{postId}/comments` |

---

## 14. TypeScript 핵심 타입

```ts
export type UserRole = "mentee" | "mentor" | "admin";

export type ConsultationStatus =
  | "collecting_context"
  | "awaiting_confirmation"
  | "analyzing"
  | "ai_answered"
  | "mentor_recommended"
  | "mentor_selected"
  | "waiting_mentor_answer"
  | "mentor_answer_processing"
  | "mentor_answered"
  | "completed"
  | "cancelled"
  | "failed";

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: {
    code: string;
    message: string;
    details?: Array<{
      field?: string;
      reason: string;
    }>;
  };
  requestId?: string;
}

export interface ConsultationSummary {
  id: string;
  title: string;
  refinedQuestion: string | null;
  status: ConsultationStatus;
  resultType: "ai_answer" | "mentor_answer" | null;
  updatedAt: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

export interface MentorRecommendation {
  rank: number;
  mentorId: string;
  displayName: string;
  currentRole: string;
  yearsOfExperience: number;
  expertise: string[];
  profileSummary: string;
  recommendationReason: string;
  matchScore: number;
  averageRating: number | null;
  expectedResponseDays: number | null;
}

export interface AsyncJob {
  jobId: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress?: number;
  currentStep?: string;
  resultUrl?: string;
}
```

---

## 15. 보안·개인정보·운영 규칙

### 15.1 인증

- Access Token은 짧게 유지하고 Refresh Token을 회전한다.
- 웹에서는 Refresh Token을 `HttpOnly`, `Secure`, `SameSite` 쿠키에 저장하는 방식을 권장한다.
- 멘토·관리자 API는 역할 기반 접근 제어를 적용한다.
- 비밀번호는 Argon2id 또는 bcrypt로 해시한다.

### 15.2 개인정보

- LLM과 멘토에게 필요한 최소 정보만 제공한다.
- 이름, 이메일, 전화번호, 주소, 주민등록번호 등 직접 식별자는 프롬프트에서 제거한다.
- 이력서 원문과 구조화 경험 데이터의 접근 권한을 분리한다.
- 상담·Q&A 로그에 API 키나 토큰을 기록하지 않는다.

### 15.3 LLM 안정성

- 모델, 프롬프트 버전, 토큰 사용량, 지연 시간, 근거 문서 ID를 기록한다.
- 외부 AI 호출에 timeout, 제한된 retry, circuit breaker를 적용한다.
- 구조화 출력은 서버 스키마로 재검증한다.
- 멘토 답변 정제 전후 내용을 감사 로그로 보존한다.
- 근거가 부족한 답변은 AI가 임의로 단정하지 않고 멘토 분기로 보낸다.

### 15.4 CORS

개발 허용 Origin 예시:

```text
http://localhost:3000
http://localhost:5173
```

운영에서는 실제 프론트엔드 도메인만 허용한다.

### 15.5 Rate Limit 권장값

| API | 권장 제한 |
| --- | --- |
| 로그인 | IP당 5회/분 |
| 상담 생성 | 사용자당 5회/시간 |
| 상담 메시지 | 사용자당 30회/10분 |
| 분석 시작 | 사용자당 10회/일 |
| Q&A 작성 | 사용자당 10회/일 |
| 댓글 작성 | 사용자당 30회/시간 |

---

## 16. 구현 전 확정이 필요한 정책

디자인 또는 운영 정책 확정 

Q&A 목록·상세 조회: 로그인 필수
정제 질문 재생성: 최대 3회

---

## 17. 변경 이력

| 버전 | 날짜 | 변경 내용 |
| --- | --- | --- |
| v1.0-draft | 2026-07-24 | 화면 자료, 기존 Agent 흐름 및 데이터 스키마를 기반으로 최초 작성 |
