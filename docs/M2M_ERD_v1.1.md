# M2M ERD v1.1 — 페르소나 멘토 구조

## 설계 원칙

- 로그인 사용자는 멘티뿐이다.
- 멘토 페르소나는 `users`와 분리된 내부 리소스다.
- 상담 원문과 재사용 자산을 분리한다.
- 답변에는 라우팅 결과, 페르소나·프롬프트·모델 버전을 기록한다.
- 재사용 동의를 철회하면 자산과 임베딩을 비활성화·삭제할 수 있어야 한다.

```mermaid
erDiagram
    USERS ||--|| MENTEE_PROFILES : has
    USERS ||--o{ REFRESH_TOKENS : owns
    USERS ||--o{ MENTEE_EXPERIENCES : records
    USERS ||--o{ CONSULTATION_SESSIONS : creates
    USERS ||--o{ QNA_POSTS : writes
    USERS ||--o{ QNA_COMMENTS : writes

    CONSULTATION_SESSIONS ||--o{ CONSULTATION_MESSAGES : contains
    CONSULTATION_SESSIONS ||--o{ ASYNC_JOBS : runs
    CONSULTATION_SESSIONS ||--o{ PERSONA_RECOMMENDATIONS : receives
    CONSULTATION_SESSIONS ||--o{ ANSWERS : produces

    MENTOR_PERSONAS ||--o{ PERSONA_RECOMMENDATIONS : recommended
    MENTOR_PERSONAS ||--o{ ANSWERS : generates

    ANSWERS ||--o| FEEDBACK : evaluated
    ANSWERS ||--o| REUSE_CONSENTS : consented
    ANSWERS ||--o| ANSWER_ASSETS : assetized

    QNA_POSTS ||--o{ QNA_COMMENTS : contains

    USERS {
        string id PK
        string email UK
        string password_hash
        string name
        string role
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    MENTEE_PROFILES {
        string id PK
        string user_id FK
        string current_status
        json background
        json considering_options
        json target_roles
        json interest_domains
        string resume_url
        string portfolio_url
    }

    CONSULTATION_SESSIONS {
        string id PK
        string mentee_id FK
        string status
        string title
        text refined_question
        int refined_question_revision_count
        string route
        string selected_persona_id FK
        string selected_persona_version
        datetime created_at
        datetime completed_at
    }

    CONSULTATION_MESSAGES {
        string id PK
        string session_id FK
        string role
        text content
        datetime created_at
    }

    MENTOR_PERSONAS {
        string id PK
        string display_name
        string current_role
        int years_of_experience
        json expertise
        text system_prompt
        string version
        boolean active
    }

    ANSWERS {
        string id PK
        string session_id FK
        string answer_type
        string route
        string persona_id FK
        string persona_version
        text raw_content
        text final_content
        float confidence_score
        string prompt_version
        string model
    }

    ANSWER_ASSETS {
        string id PK
        string answer_id FK
        text anonymized_question
        text anonymized_answer
        string privacy_check_status
        string quality_check_status
        string embedding_id
        boolean active
        datetime deleted_at
    }
```

## 정제 질문 재생성 제약

`consultation_sessions.refined_question_revision_count`의 허용 범위는 `0..3`이다.

- 최초 생성: `0`
- AI 재생성 성공: `+1`
- 직접 수정: 증가하지 않음
- AI 호출 실패: 증가하지 않음
- `3`이면 재생성 API는 `409 REFINED_QUESTION_REVISION_LIMIT_EXCEEDED`

