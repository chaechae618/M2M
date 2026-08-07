export type MessageRole = "user" | "assistant";

export type MessageKind =
  | "text"
  | "refined_question"
  | "mentor_recommendations"
  | "mentor_confirmation"
  | "mentor_request_status"
  | "mentor_request_editor"
  | "answer_feedback"
  | "job_retry";

export type ChatMessage = {
  id: string;
  role: MessageRole;
  kind: MessageKind;
  text?: string;
  compact?: boolean;
  mentors?: MentorRecommendation[];
  answerId?: string;
  jobId?: string;
  retryKind?: "analysis" | "persona";
  progress?: number;
  feedbackStep?: "rating" | "consent" | "done";
};

export type ApiChatMessage = {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
};

export type RefinedQuestion = {
  content: string | null;
};

export type ConsultationSession = {
  id: string;
  title: string;
  status: string;
  refinedQuestion: string | null;
  route: string | null;
};

export type MentorRecommendation = {
  personaId: string;
  displayName: string;
  currentRole: string;
  yearsOfExperience: number;
  expertise: string[] | Record<string, unknown>;
  profileSummary: string;
  recommendationReason: string;
  matchScore: number;
};

export type Job = {
  jobId: string;
  jobType: string;
  status: string;
  progress: number;
  currentStep: string;
  error?: { message?: string; retryable?: boolean } | null;
};

export type ConsultationAnswer = {
  id: string;
  content: string;
  summary?: string | null;
  answerType?: string;
  route?: string;
};

export type ConsultationFeedback = {
  id: string;
  answerId: string;
  rating: number;
  createdAt: string;
};

export type ConsultationConsent = {
  id: string;
  answerId: string;
  consent: boolean;
  scope: string;
  createdAt: string;
  updatedAt: string;
};

export type ConsultationDetail = {
  session: ConsultationSession;
  messages: ApiChatMessage[];
  refinedQuestion: { content: string } | null;
  latestJob: Job | null;
  answer: ConsultationAnswer | null;
  feedback: ConsultationFeedback | null;
  reuseConsent: ConsultationConsent | null;
};

export type ConsultationResult = {
  status: string;
  route: string | null;
  reason?: string | null;
  answer: ConsultationAnswer | null;
};
