from enum import StrEnum


class UserRole(StrEnum):
    MENTEE = "mentee"


class CurrentStatus(StrEnum):
    STUDENT = "student"
    JOB_SEEKER = "job_seeker"
    CAREER_CHANGE = "career_change"
    EMPLOYED = "employed"
    OTHER = "other"


class ConsultationStatus(StrEnum):
    COLLECTING_CONTEXT = "collecting_context"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    ANALYZING = "analyzing"
    AI_ANSWERED = "ai_answered"
    PERSONA_RECOMMENDED = "persona_recommended"
    PERSONA_ANSWER_GENERATING = "persona_answer_generating"
    PERSONA_ANSWERED = "persona_answered"
    AWAITING_FEEDBACK = "awaiting_feedback"
    ASSETIZING = "assetizing"
    ASSETIZED = "assetized"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AnswerRoute(StrEnum):
    LLM_DIRECT = "llm_direct"
    PARTIAL_WITH_MENTOR_SUGGEST = "partial_with_mentor_suggest"
    MENTOR_NEEDED = "mentor_needed"


class AnswerType(StrEnum):
    GENERAL_AI = "general_ai"
    PERSONA_AI = "persona_ai"


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
