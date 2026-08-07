import { apiRequest, jsonRequest } from "@/shared/api/client";
import type {
  ApiChatMessage,
  ConsultationDetail,
  ConsultationResult,
  ConsultationSession,
  Job,
  MentorRecommendation,
  RefinedQuestion,
} from "@/features/consultation/model/types";

export class JobFailedError extends Error {
  constructor(
    public jobId: string,
    message: string,
    public retryable: boolean,
  ) {
    super(message);
  }
}

type WaitForJobOptions = {
  signal?: AbortSignal;
  onProgress?: (job: Job) => void;
};

function waitForNextPoll(signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(resolve, 1000);
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timeout);
        reject(new DOMException("Polling aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

export async function waitForJob(jobId: string, options: WaitForJobOptions = {}) {
  for (let attempt = 0; attempt < 180; attempt += 1) {
    const job = await apiRequest<Job>(`jobs/${jobId}`, { signal: options.signal });
    options.onProgress?.(job);
    if (job.status === "completed") return;
    if (job.status === "failed") {
      throw new JobFailedError(
        jobId,
        job.error?.message ?? "답변 생성 작업에 실패했습니다.",
        Boolean(job.error?.retryable),
      );
    }
    await waitForNextPoll(options.signal);
  }
  throw new JobFailedError(
    jobId,
    "답변 생성 시간이 길어지고 있습니다. 잠시 후 다시 시도해주세요.",
    false,
  );
}

export function getConsultation(sessionId: string) {
  return apiRequest<ConsultationDetail>(`consultations/${sessionId}`);
}

export function createConsultation(content: string) {
  return apiRequest<{ session: ConsultationSession; assistantMessage: ApiChatMessage }>(
    "consultations",
    jsonRequest("POST", { initialMessage: content }),
  );
}

export function addConsultationMessage(sessionId: string, content: string) {
  return apiRequest<{
    sessionStatus: string;
    needMoreInfo: boolean;
    assistantMessage: ApiChatMessage | null;
    refinedQuestion: RefinedQuestion | null;
  }>(`consultations/${sessionId}/messages`, jsonRequest("POST", { content }));
}

export function getConsultationResult(sessionId: string) {
  return apiRequest<ConsultationResult>(`consultations/${sessionId}/result`);
}

export function getMentorRecommendations(sessionId: string) {
  return apiRequest<{ personas: MentorRecommendation[] }>(
    `consultations/${sessionId}/persona-recommendations`,
  );
}

export function confirmRefinedQuestion(sessionId: string) {
  return apiRequest<{ jobId: string }>(`consultations/${sessionId}/confirm`, {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
  });
}

export function cancelConsultation(sessionId: string) {
  return apiRequest(`consultations/${sessionId}`, { method: "DELETE" });
}

export function selectMentor(sessionId: string, personaId: string) {
  return apiRequest<{ jobId: string }>(
    `consultations/${sessionId}/persona-selection`,
    {
      ...jsonRequest("POST", { personaId }),
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
    },
  );
}

export function updateRefinedQuestion(sessionId: string, content: string) {
  return apiRequest<{ refinedQuestion: RefinedQuestion }>(
    `consultations/${sessionId}/refined-question`,
    jsonRequest("PATCH", { content }),
  );
}

export function retryJob(jobId: string) {
  return apiRequest(`jobs/${jobId}/retry`, { method: "POST" });
}
