# M2M API 명세서 정정 전·후 비교

## 비교 대상

| 구분 | 문서 | 의미 |
| --- | --- | --- |
| 정정 전 | `M2M_API_명세서_v1.0.md` | 실제 사람 멘토를 전제로 한 초기 초안 |
| 정정 후 | `M2M_API_명세서_v1.1_페르소나.md` | AI 멘토 페르소나를 전제로 한 구현 기준안 |

---

## 1. 핵심 가정 비교

| 항목 | 정정 전 v1.0 | 정정 후 v1.1 |
| --- | --- | --- |
| 로그인 사용자 | 멘티·멘토 | 멘티만 |
| 멘토의 정체 | 실제 사람 | 사전에 만든 LLM 페르소나 |
| 멘토 등록 | 관리자가 멘토 계정 발급 | 페르소나 데이터·프롬프트 등록 |
| 멘토 인증 | 발급 계정으로 로그인 | 인증 없음 |
| 질문 전달 | 실제 멘토 질문함으로 전달 | 선택된 페르소나 프롬프트로 LLM 호출 |
| 답변 대기 | 멘토가 작성할 때까지 대기 | 비동기 LLM 작업 완료까지 대기 |
| 답변 거절 | 가능 | 없음 |
| 답변 기한 | 필요 | 없음 |
| 재사용 동의 | 멘티·멘토 양쪽 동의 | 멘티 동의만 필요 |
| Q&A | 선택 인증 | 목록·상세 포함 로그인 필수 |

---

## 2. 전체 흐름 비교

### 정정 전

```text
Agent 2 mentor_needed
→ 실제 멘토 Top 3 추천
→ 멘티가 멘토 선택
→ 실제 멘토 질문함으로 전달
→ 멘토 수락 또는 거절
→ 멘토 답변 작성
→ LLM 후처리
→ 멘티에게 전달
→ 멘티·멘토 재사용 동의
```

### 정정 후

```text
Agent 2 mentor_needed
→ Agent 3 페르소나 Top 3 추천
→ 멘티가 페르소나 선택
→ 선택된 페르소나 프롬프트로 LLM 답변 생성
→ 멘티에게 전달
→ 만족도 평가
→ 멘티 재사용 동의
→ 개인정보·품질 검사
→ RAG 자산 및 임베딩 저장
```

### 변경 효과

- 실제 멘토 응답을 기다리는 시간이 사라진다.
- 멘토 수락·거절·기한·알림 로직이 필요 없어진다.
- 대신 페르소나 버전, 프롬프트 버전, LLM timeout과 retry 관리가 중요해진다.
- 페르소나가 실제 사람으로 오인되지 않도록 AI 표시가 필요해진다.

---

## 3. 상담 상태 비교

| 정정 전 상태 | 정정 후 상태 | 변경 이유 |
| --- | --- | --- |
| `mentor_recommended` | `persona_recommended` | 추천 대상이 실제 멘토가 아님 |
| `mentor_selected` | 제거 | 선택과 동시에 LLM 작업 시작 가능 |
| `waiting_mentor_answer` | 제거 | 사람 답변 대기 없음 |
| `mentor_answer_processing` | `persona_answer_generating` | LLM이 답변을 직접 생성 |
| `mentor_answered` | `persona_answered` | 페르소나 AI 답변 완료 |
| 없음 | `awaiting_feedback` | 평가·동의 단계 명시 |
| 없음 | `assetizing` | 개인정보·품질 검사 진행 |
| 없음 | `assetized` | RAG 자산 저장 완료 |

---

## 4. API 변경 비교

### 4.1 삭제된 API

실제 사람 멘토가 없으므로 다음 API를 v1.1에서 삭제했다.

```http
GET   /mentor/questions
GET   /mentor/questions/{assignmentId}
POST  /mentor/questions/{assignmentId}/accept
POST  /mentor/questions/{assignmentId}/decline
POST  /mentor/questions/{assignmentId}/answers
GET   /mentor/questions/{assignmentId}/answers/{answerId}
PUT   /mentor/answers/{answerId}/reuse-consent

GET   /admin/mentors
POST  /admin/mentors
PATCH /admin/mentors/{mentorId}
POST  /admin/mentors/{mentorId}/invite
```

### 4.2 이름과 의미가 변경된 API

| 정정 전 | 정정 후 | 변경 |
| --- | --- | --- |
| `GET /consultations/{id}/mentor-recommendations` | `GET /consultations/{id}/persona-recommendations` | 실제 멘토 → AI 페르소나 |
| `POST /consultations/{id}/mentor-selection` | `POST /consultations/{id}/persona-selection` | 질문 전달 → LLM 답변 생성 시작 |

### 4.3 새로 추가된 API

```http
POST /consultations/{sessionId}/refined-question/regenerate
GET  /consultations/{sessionId}/assetization
```

추가 이유:

- 정제 질문 재생성 3회 정책을 별도 API로 명확히 관리한다.
- 자산화의 개인정보 검사·품질 검사·임베딩 상태를 조회한다.

페르소나 답변 재생성 API는 허용 여부와 횟수가 결정되지 않아 v1 구현 범위에서 제외했다.

---

## 5. 정제 질문 정책 비교

| 항목 | 정정 전 | 정정 후 |
| --- | --- | --- |
| AI 재생성 횟수 | 미정 | 최대 3회 |
| 최초 생성 | 별도 정의 없음 | 횟수에서 제외 |
| 직접 수정 | 허용 | 허용, 횟수에서 제외 |
| 실패한 LLM 호출 | 별도 정의 없음 | 횟수 차감 안 함 |
| 확정 이후 수정 | 별도 정의 없음 | 불가 |
| 프론트 표시 | 없음 | `재생성 1/3` 표시 |

정정 후 응답 필드:

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

---

## 6. Q&A 정책 비교

| 기능 | 정정 전 | 정정 후 |
| --- | --- | --- |
| 목록 조회 | 인증 선택 | 로그인 필수 |
| 상세 조회 | 인증 선택 | 로그인 필수 |
| 작성 | 멘티 | 멘티 |
| 댓글 | 로그인 사용자 | 멘티 |
| 실제 멘토 댓글 | 가능성 존재 | 없음 |
| 페르소나 자동 댓글 | 미정 | 현재 범위 제외 |

비로그인 사용자의 모든 `/qna/*` 요청은 다음 오류를 반환한다.

```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "로그인이 필요합니다."
  }
}
```

---

## 7. 데이터 모델 비교

### 삭제 또는 불필요해진 데이터

```text
mentor_users
mentor_login_credentials
mentor_assignments
mentor_question_inbox
mentor_acceptance
mentor_decline_reason
mentor_answer_due_at
mentor_reuse_consent
```

### 새로 중요해진 데이터

```text
mentor_personas
- persona_id
- display_name
- career setting
- expertise
- answer_style
- matching_summary
- system_prompt
- persona_version
- active

answers
- route
- answer_type
- persona_id
- persona_version
- prompt_version
- model

answer_assets
- anonymized_question
- anonymized_answer
- privacy_check_status
- quality_check_status
- embedding_id
- active
```

---

## 8. 응답 객체 비교

### 정정 전 실제 멘토 객체

```json
{
  "mentorId": "mtr_001",
  "displayName": "김OO",
  "currentRole": "핀테크 데이터 분석가",
  "yearsOfExperience": 6,
  "expectedResponseDays": 3,
  "averageRating": 4.8
}
```

### 정정 후 페르소나 객체

```json
{
  "personaId": "persona_finance_da_01",
  "displayName": "금융 데이터 분석 멘토",
  "currentRole": "핀테크 데이터 분석가",
  "yearsOfExperience": 6,
  "personaVersion": "1.2",
  "isAiPersona": true,
  "matchScore": 0.91
}
```

삭제된 필드:

- `expectedResponseDays`
- 실제 인물의 `averageRating`
- 멘토 계정·활동 상태

추가된 필드:

- `personaVersion`
- `isAiPersona`
- 답변 생성 모델·프롬프트 버전

---

## 9. 재사용 동의 비교

### 정정 전

```text
멘티 동의
AND 실제 멘토 동의
AND 개인정보 검사
AND 품질 검사
```

### 정정 후

```text
멘티 동의
AND 개인정보 검사
AND 품질 검사
AND 답변 완료
```

철회 시 처리:

- 다른 멘티의 RAG 검색에서 즉시 제외
- 익명화 자산 삭제
- 파생 임베딩 삭제
- 검색 캐시 삭제
- 개인 상담 기록은 유지

---

## 10. 프론트엔드 변경

### 삭제

- 멘토 회원가입 탭
- 멘토 로그인 화면
- 멘토 질문함
- 질문 수락·거절
- 답변 기한 표시
- 멘토 답변 작성 화면

### 변경

- “멘토 추천”을 “AI 멘토 페르소나 추천”으로 표시
- 페르소나 카드에 `AI 페르소나` 배지 표시
- 실제 인물의 프로필로 오인할 수 있는 표현 제거
- 페르소나 선택 후 “답변 대기” 대신 “AI 답변 생성 중” 표시

### 추가

- 정제 질문 화면에 `재생성 n/3` 표시
- 만족도 평가
- 재사용 동의
- 자산화 처리 상태

---

## 11. 백엔드 구현 영향

### 제거 가능한 구현

- 멘토 인증·권한
- 멘토 알림
- 질문 배정·수락·거절
- 답변 기한 scheduler
- 실제 멘토 답변 CRUD
- 멘토 동의 관리

### 새로 필요한 구현

- 페르소나 Repository
- 페르소나 버전 관리
- Agent 3 추천 결과 검증
- 선택한 페르소나 프롬프트 조립
- 페르소나 LLM 작업 큐
- AI 페르소나 표시 필드
- 정제 질문 재생성 횟수의 원자적 증가
- 만족도·동의 기반 자산화
- 임베딩 삭제 및 검색 제외

---

## 12. 구현 기준

백엔드 구현은 `M2M_API_명세서_v1.1_페르소나.md`를 기준으로 한다.

`M2M_API_명세서_v1.0.md`의 다음 영역은 구현하지 않는다.

- 멘토 인증
- 관리자 멘토 계정 발급
- 멘토 질문함
- 질문 수락·거절
- 사람 멘토 답변
- 멘토 재사용 동의
