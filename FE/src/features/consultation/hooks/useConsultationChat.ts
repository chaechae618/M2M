"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  JobFailedError,
  addConsultationMessage,
  cancelConsultation,
  confirmRefinedQuestion,
  createConsultation,
  getConsultation,
  getConsultationResult,
  getMentorRecommendations,
  retryJob,
  selectMentor,
  updateRefinedQuestion,
  waitForJob,
} from "@/features/consultation/api/consultations";
import type {
  ApiChatMessage,
  ChatMessage,
  ConsultationAnswer,
  ConsultationDetail,
  Job,
  MentorRecommendation,
} from "@/features/consultation/model/types";
import { notifyConsultationsChanged } from "@/features/consultation/model/events";
import { ApiError, apiRequest } from "@/shared/api/client";
import type { AuthUser } from "@/shared/api/types";
import { routes } from "@/shared/constants/routes";

function apiMessage(message: ApiChatMessage): ChatMessage {
  return { id: message.id, role: message.role, kind: "text", text: message.content };
}

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

function retryKindForJob(jobType: string): "analysis" | "persona" | null {
  if (jobType === "consultation_analysis") return "analysis";
  if (jobType === "persona_answer_generation") return "persona";
  return null;
}

function jobStatusText(job: Job) {
  const labels: Record<string, string> = {
    waiting_for_agent2: "질문 분석을 준비하고 있어요",
    agent2_search_and_route: "기존 지식으로 답할 수 있는지 확인하고 있어요",
    agent3_mentor_matching: "질문과 잘 맞는 AI 멘토를 찾고 있어요",
    waiting_for_persona: "선택한 AI 멘토에게 질문을 전달하고 있어요",
    persona_answer_generation: "선택한 AI 멘토가 답변을 작성하고 있어요",
    waiting_for_assetization: "공개 가능한 답변으로 정리하고 있어요",
    completed: "처리가 완료되었어요",
  };
  return labels[job.currentStep] ?? "요청을 처리하고 있어요";
}

function answerMessages(
  answer: ConsultationAnswer,
  feedbackStep: "rating" | "consent" | "done" = "rating",
): ChatMessage[] {
  return [
    {
      id: `a-answer-${answer.id}`,
      role: "assistant",
      kind: "text",
      text: answer.content,
    },
    {
      id: `a-feedback-${answer.id}`,
      role: "assistant",
      kind: "answer_feedback",
      answerId: answer.id,
      feedbackStep,
    },
  ];
}

export function useConsultationChat({
  startsAsNewChat,
  resumeSessionId,
}: {
  startsAsNewChat: boolean;
  resumeSessionId: string | null;
}) {
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isNewChat, setIsNewChat] = useState(startsAsNewChat);
  const [question, setQuestion] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<string | null>(null);
  const [sessionTitle, setSessionTitle] = useState("새 상담");
  const [refinedQuestion, setRefinedQuestion] = useState("");
  const [selectedMentor, setSelectedMentor] = useState<MentorRecommendation | null>(null);
  const [userName, setUserName] = useState("이름");
  const [isBusy, setIsBusy] = useState(false);
  const actionLockRef = useRef(false);
  const mentorSelectionLockedRef = useRef(false);
  const activeJobControllerRef = useRef<AbortController | null>(null);

  const isActive = question.trim().length > 0;
  const canCompose = !sessionId || sessionStatus === "collecting_context";
  const lastMessage = messages[messages.length - 1];
  const showRefinedChoices = lastMessage?.kind === "refined_question";

  useEffect(() => {
    apiRequest<AuthUser>("auth/me")
      .then((user) => setUserName(user.name))
      .catch((requestError) => {
        if (requestError instanceof ApiError && requestError.status === 401) {
          router.replace(routes.login);
        }
      });
  }, [router]);

  useEffect(() => () => activeJobControllerRef.current?.abort(), []);

  function tryLockAction() {
    if (actionLockRef.current) return false;
    actionLockRef.current = true;
    return true;
  }

  function unlockAction() {
    actionLockRef.current = false;
  }

  function beginJobWait() {
    activeJobControllerRef.current?.abort();
    const controller = new AbortController();
    activeJobControllerRef.current = controller;
    return controller;
  }

  function finishJobWait(controller: AbortController) {
    if (activeJobControllerRef.current === controller) {
      activeJobControllerRef.current = null;
    }
  }

  function appendMessages(nextMessages: ChatMessage[]) {
    setMessages((current) => {
      const withoutEditor = current.filter((message) => message.kind !== "mentor_request_editor");
      return [...withoutEditor, ...nextMessages];
    });
  }

  function updateMessage(messageId: string, updates: Partial<ChatMessage>) {
    setMessages((current) =>
      current.map((message) => (message.id === messageId ? { ...message, ...updates } : message)),
    );
  }

  function appendError(requestError: unknown) {
    if (isAbortError(requestError)) return;
    appendMessages([
      {
        id: `a-error-${Date.now()}`,
        role: "assistant",
        kind: "text",
        text: requestError instanceof Error ? requestError.message : "요청을 처리하지 못했습니다.",
      },
    ]);
  }

  function appendJobError(requestError: unknown, retryKind: "analysis" | "persona") {
    if (isAbortError(requestError)) return;
    if (requestError instanceof JobFailedError && requestError.retryable) {
      appendMessages([
        {
          id: `a-job-error-${Date.now()}`,
          role: "assistant",
          kind: "job_retry",
          text: requestError.message,
          jobId: requestError.jobId,
          retryKind,
        },
      ]);
      return;
    }
    appendError(requestError);
  }

  function trackJob(statusMessageId: string) {
    return (job: Job) => {
      updateMessage(statusMessageId, {
        text: jobStatusText(job),
        progress: job.progress,
      });
    };
  }

  async function finishAnalysis(currentSessionId: string) {
    const result = await getConsultationResult(currentSessionId);
    setSessionStatus(result.status);
    notifyConsultationsChanged();
    if (result.route === "llm_direct" && result.answer) {
      appendMessages(answerMessages(result.answer));
      return;
    }

    const recommendations = await getMentorRecommendations(currentSessionId);
    const nextMessages: ChatMessage[] = [];
    if (result.route === "partial_with_mentor_suggest" && result.answer) {
      nextMessages.push({
        id: `a-partial-answer-${result.answer.id}`,
        role: "assistant",
        kind: "text",
        text: result.answer.content,
      });
    }
    nextMessages.push({
      id: `a-mentors-${Date.now()}`,
      role: "assistant",
      kind: "mentor_recommendations",
      mentors: recommendations.personas,
    });
    appendMessages(nextMessages);
  }

  async function finishPersonaAnswer(currentSessionId: string) {
    const result = await getConsultationResult(currentSessionId);
    if (!result.answer) throw new Error("생성된 답변을 찾지 못했습니다.");
    setSessionStatus(result.status);
    appendMessages(answerMessages(result.answer));
    notifyConsultationsChanged();
  }

  async function resumeJob(
    detail: ConsultationDetail,
    statusMessageId: string,
    retryKind: "analysis" | "persona",
    signal: AbortSignal,
  ) {
    const job = detail.latestJob;
    if (!job) {
      appendMessages([
        {
          id: `a-missing-job-${Date.now()}`,
          role: "assistant",
          kind: "text",
          text: "진행 중인 작업 정보를 찾지 못했어요. 잠시 후 새 대화로 다시 시도해주세요.",
        },
      ]);
      return;
    }

    if (job.status === "failed") {
      appendJobError(
        new JobFailedError(
          job.jobId,
          job.error?.message ?? "작업을 완료하지 못했습니다.",
          Boolean(job.error?.retryable),
        ),
        retryKind,
      );
      return;
    }

    setIsBusy(true);
    try {
      await waitForJob(job.jobId, { signal, onProgress: trackJob(statusMessageId) });
      if (retryKind === "analysis") {
        await finishAnalysis(detail.session.id);
      } else {
        await finishPersonaAnswer(detail.session.id);
      }
    } catch (requestError) {
      appendJobError(requestError, retryKind);
    } finally {
      if (!signal.aborted) setIsBusy(false);
    }
  }

  useEffect(() => {
    if (!resumeSessionId) return;

    const controller = new AbortController();
    async function loadSession() {
      try {
        const detail = await getConsultation(resumeSessionId as string);
        if (controller.signal.aborted) return;

        setSessionId(detail.session.id);
        setSessionStatus(detail.session.status);
        setSessionTitle(detail.session.title);
        setRefinedQuestion(detail.session.refinedQuestion ?? "");
        const hydrated = detail.messages.map(apiMessage);
        const status = detail.session.status;

        if (status === "awaiting_confirmation" && detail.session.refinedQuestion) {
          hydrated.push({
            id: `a-refined-resume-${detail.session.id}`,
            role: "assistant",
            kind: "refined_question",
            text: detail.session.refinedQuestion,
          });
          setMessages(hydrated);
          return;
        }

        if (status === "analyzing") {
          const statusId = `a-analysis-resume-${detail.session.id}`;
          hydrated.push({
            id: statusId,
            role: "assistant",
            kind: "mentor_request_status",
            text: detail.latestJob ? jobStatusText(detail.latestJob) : "질문을 분석하고 있어요",
            progress: detail.latestJob?.progress ?? 0,
          });
          setMessages(hydrated);
          await resumeJob(detail, statusId, "analysis", controller.signal);
          return;
        }

        if (status === "persona_recommended") {
          if (detail.answer) {
            hydrated.push({
              id: `a-partial-answer-${detail.answer.id}`,
              role: "assistant",
              kind: "text",
              text: detail.answer.content,
            });
          }
          setMessages(hydrated);
          const recommendations = await getMentorRecommendations(detail.session.id);
          if (!controller.signal.aborted) {
            appendMessages([
              {
                id: `a-mentors-resume-${detail.session.id}`,
                role: "assistant",
                kind: "mentor_recommendations",
                mentors: recommendations.personas,
              },
            ]);
          }
          return;
        }

        if (status === "persona_answer_generating") {
          const statusId = `a-persona-resume-${detail.session.id}`;
          hydrated.push({
            id: statusId,
            role: "assistant",
            kind: "mentor_request_status",
            text: detail.latestJob ? jobStatusText(detail.latestJob) : "AI 멘토가 답변을 작성하고 있어요",
            progress: detail.latestJob?.progress ?? 0,
          });
          setMessages(hydrated);
          await resumeJob(detail, statusId, "persona", controller.signal);
          return;
        }

        if (status === "failed") {
          setMessages(hydrated);
          const latestJob = detail.latestJob;
          const retryKind = latestJob ? retryKindForJob(latestJob.jobType) : null;
          if (latestJob && retryKind) {
            appendJobError(
              new JobFailedError(
                latestJob.jobId,
                latestJob.error?.message ?? "작업을 완료하지 못했습니다.",
                Boolean(latestJob.error?.retryable),
              ),
              retryKind,
            );
          } else {
            appendError(new Error("상담 처리에 실패했습니다. 새 대화에서 다시 시도해주세요."));
          }
          return;
        }

        if (detail.answer) {
          let feedbackStep: "rating" | "consent" | "done" = "rating";
          if (detail.feedback) feedbackStep = detail.reuseConsent ? "done" : "consent";
          if (["completed", "assetized"].includes(status)) feedbackStep = "done";
          hydrated.push(...answerMessages(detail.answer, feedbackStep));
        }
        setMessages(hydrated);

        if (status === "assetizing" && detail.latestJob) {
          const statusId = `a-asset-resume-${detail.session.id}`;
          appendMessages([
            {
              id: statusId,
              role: "assistant",
              kind: "mentor_request_status",
              text: jobStatusText(detail.latestJob),
              progress: detail.latestJob.progress,
            },
          ]);
          setIsBusy(true);
          try {
            await waitForJob(detail.latestJob.jobId, {
              signal: controller.signal,
              onProgress: trackJob(statusId),
            });
            await apiRequest(`consultations/${detail.session.id}/complete`, { method: "POST" });
            setSessionStatus("completed");
            updateMessage(statusId, { text: "답변 정리가 완료되었어요", progress: 100 });
            notifyConsultationsChanged();
          } catch (requestError) {
            appendError(requestError);
          } finally {
            if (!controller.signal.aborted) setIsBusy(false);
          }
        }
      } catch (requestError) {
        appendError(requestError);
      }
    }

    loadSession();
    return () => controller.abort();
    // Hydration runs once per session URL and uses functional state updates.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resumeSessionId]);

  async function submitQuestion() {
    const content = question.trim();
    if (!content || isBusy || !canCompose || !tryLockAction()) return;

    const thinkingId = `a-thinking-${Date.now()}`;
    setQuestion("");
    setIsNewChat(false);
    appendMessages([
      { id: `u-${Date.now()}`, role: "user", kind: "text", text: content },
      {
        id: thinkingId,
        role: "assistant",
        kind: "mentor_request_status",
        text: "답변을 준비하고 있어요",
      },
    ]);
    setIsBusy(true);
    try {
      if (!sessionId) {
        const created = await createConsultation(content);
        setMessages((current) => current.filter((message) => message.id !== thinkingId));
        setSessionId(created.session.id);
        setSessionStatus(created.session.status);
        setSessionTitle(created.session.title);
        notifyConsultationsChanged();
        if (created.session.refinedQuestion) {
          setRefinedQuestion(created.session.refinedQuestion);
          appendMessages([
            {
              id: `a-refined-${Date.now()}`,
              role: "assistant",
              kind: "refined_question",
              text: created.session.refinedQuestion,
            },
          ]);
        } else {
          appendMessages([apiMessage(created.assistantMessage)]);
        }
        router.replace(`/chat?session=${created.session.id}`, { scroll: false });
      } else {
        const result = await addConsultationMessage(sessionId, content);
        setSessionStatus(result.sessionStatus);
        setMessages((current) => current.filter((message) => message.id !== thinkingId));
        if (result.refinedQuestion?.content) {
          setRefinedQuestion(result.refinedQuestion.content);
          appendMessages([
            {
              id: `a-refined-${Date.now()}`,
              role: "assistant",
              kind: "refined_question",
              text: result.refinedQuestion.content,
            },
          ]);
        } else if (result.assistantMessage) {
          appendMessages([apiMessage(result.assistantMessage)]);
        }
        notifyConsultationsChanged();
      }
    } catch (requestError) {
      setMessages((current) => current.filter((message) => message.id !== thinkingId));
      appendError(requestError);
    } finally {
      setIsBusy(false);
      unlockAction();
    }
  }

  async function retryFailedJob(jobId: string, retryKind: "analysis" | "persona") {
    if (!sessionId || isBusy || !tryLockAction()) return;
    const controller = beginJobWait();
    const statusId = `a-retry-status-${Date.now()}`;
    appendMessages([
      {
        id: statusId,
        role: "assistant",
        kind: "mentor_request_status",
        text: "작업을 다시 시작하고 있어요",
        progress: 0,
      },
    ]);
    setIsBusy(true);
    try {
      await retryJob(jobId);
      notifyConsultationsChanged();
      await waitForJob(jobId, { signal: controller.signal, onProgress: trackJob(statusId) });
      if (retryKind === "analysis") {
        await finishAnalysis(sessionId);
      } else {
        await finishPersonaAnswer(sessionId);
      }
    } catch (requestError) {
      appendJobError(requestError, retryKind);
    } finally {
      finishJobWait(controller);
      if (!controller.signal.aborted) setIsBusy(false);
      unlockAction();
    }
  }

  async function sendRefinedQuestion() {
    if (!sessionId || isBusy || !tryLockAction()) return;
    const controller = beginJobWait();
    const statusId = `a-analyzing-${Date.now()}`;
    appendMessages([
      {
        id: `u-refined-send-${Date.now()}`,
        role: "user",
        kind: "text",
        compact: true,
        text: "이 질문으로 보내기",
      },
      {
        id: statusId,
        role: "assistant",
        kind: "mentor_request_status",
        text: "질문 분석을 준비하고 있어요",
        progress: 0,
      },
    ]);
    setIsBusy(true);
    try {
      const confirmation = await confirmRefinedQuestion(sessionId);
      setSessionStatus("analyzing");
      notifyConsultationsChanged();
      await waitForJob(confirmation.jobId, { signal: controller.signal, onProgress: trackJob(statusId) });
      await finishAnalysis(sessionId);
    } catch (requestError) {
      appendJobError(requestError, "analysis");
    } finally {
      finishJobWait(controller);
      if (!controller.signal.aborted) setIsBusy(false);
      unlockAction();
    }
  }

  async function cancelRefinedQuestion() {
    if (!sessionId || isBusy || !tryLockAction()) return;
    try {
      await cancelConsultation(sessionId);
    } catch (requestError) {
      appendError(requestError);
      unlockAction();
      return;
    }
    appendMessages([
      {
        id: `u-refined-cancel-${Date.now()}`,
        role: "user",
        kind: "text",
        compact: true,
        text: "아직 보내지 않을게",
      },
      {
        id: `a-refined-cancel-${Date.now()}`,
        role: "assistant",
        kind: "text",
        text: "좋아요. 새로운 고민은 새 대화에서 다시 시작할 수 있어요.",
      },
    ]);
    setSessionId(null);
    setSessionStatus("cancelled");
    setRefinedQuestion("");
    setSelectedMentor(null);
    notifyConsultationsChanged();
    router.replace(`/chat?new=${Date.now()}`, { scroll: false });
    unlockAction();
  }

  function chooseMentor(mentor: MentorRecommendation) {
    if (isBusy || selectedMentor || mentorSelectionLockedRef.current) return;
    mentorSelectionLockedRef.current = true;
    setSelectedMentor(mentor);
    appendMessages([
      {
        id: `u-mentor-select-${Date.now()}`,
        role: "user",
        kind: "text",
        compact: true,
        text: `${mentor.displayName} 멘토를 선택할게`,
      },
      { id: `a-mentor-confirm-${Date.now()}`, role: "assistant", kind: "mentor_confirmation" },
    ]);
  }

  async function confirmMentorRequest() {
    if (!sessionId || !selectedMentor || isBusy || !tryLockAction()) return;
    const controller = beginJobWait();
    const statusId = `a-persona-status-${Date.now()}`;
    appendMessages([
      {
        id: `u-mentor-confirm-${Date.now()}`,
        role: "user",
        kind: "text",
        compact: true,
        text: "질문 보내기",
      },
      {
        id: statusId,
        role: "assistant",
        kind: "mentor_request_status",
        text: "선택한 AI 멘토에게 질문을 전달하고 있어요",
        progress: 0,
      },
    ]);
    setIsBusy(true);
    try {
      const selection = await selectMentor(sessionId, selectedMentor.personaId);
      setSessionStatus("persona_answer_generating");
      notifyConsultationsChanged();
      await waitForJob(selection.jobId, { signal: controller.signal, onProgress: trackJob(statusId) });
      await finishPersonaAnswer(sessionId);
    } catch (requestError) {
      appendJobError(requestError, "persona");
    } finally {
      finishJobWait(controller);
      if (!controller.signal.aborted) setIsBusy(false);
      unlockAction();
    }
  }

  function editRefinedQuestion() {
    appendMessages([
      { id: `editor-${Date.now()}`, role: "assistant", kind: "mentor_request_editor" },
    ]);
  }

  async function completeQuestionEdit(content: string) {
    if (!sessionId || content.trim().length < 10 || isBusy || !tryLockAction()) return;
    setIsBusy(true);
    try {
      const result = await updateRefinedQuestion(sessionId, content.trim());
      const nextQuestion = result.refinedQuestion.content ?? content.trim();
      setRefinedQuestion(nextQuestion);
      setMessages((current) => [
        ...current.filter((message) => message.kind !== "mentor_request_editor"),
        { id: `u-edit-complete-${Date.now()}`, role: "user", kind: "text", compact: true, text: "수정완료" },
        { id: `a-refined-again-${Date.now()}`, role: "assistant", kind: "refined_question", text: nextQuestion },
      ]);
      notifyConsultationsChanged();
    } catch (requestError) {
      appendError(requestError);
    } finally {
      setIsBusy(false);
      unlockAction();
    }
  }

  return {
    messages,
    isNewChat,
    question,
    setQuestion,
    sessionId,
    sessionStatus,
    sessionTitle,
    refinedQuestion,
    selectedMentor,
    userName,
    isBusy,
    isActive,
    canCompose,
    showRefinedChoices,
    submitQuestion,
    retryFailedJob,
    sendRefinedQuestion,
    cancelRefinedQuestion,
    chooseMentor,
    confirmMentorRequest,
    editRefinedQuestion,
    completeQuestionEdit,
  };
}
