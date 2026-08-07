"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { CheckCircle2, ChevronDown, LoaderCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { waitForJob } from "@/features/consultation/api/consultations";
import type { ChatMessage, MentorRecommendation } from "@/features/consultation/model/types";
import { notifyConsultationsChanged } from "@/features/consultation/model/events";
import { apiRequest, jsonRequest } from "@/shared/api/client";
import { cn } from "@/shared/lib/cn";
import { ServiceBottomNavigation } from "@/widgets/service-bottom-navigation/ServiceBottomNavigation";

const assets = {
  avatar: "/figma-assets/chat/avatar-person.svg",
  backgroundBottom: "/figma-assets/chat/bg-ellipse-744.svg",
  backgroundCenter: "/figma-assets/chat/bg-ellipse-743.svg",
  backgroundLeft: "/figma-assets/chat/bg-ellipse-742.svg",
  backgroundRight: "/figma-assets/chat/bg-ellipse-745.svg",
  chat: "/figma-assets/chat/chat.svg",
  editLine: "/figma-assets/chat/edit-line.svg",
  sendActive: "/figma-assets/chat/send-active.svg",
  sendDisabled: "/figma-assets/chat/send-disabled.svg",
  writeNew: "/figma-assets/chat/write-new.svg",
};

type ChatScreenProps = {
  messages: ChatMessage[];
  isNewChat: boolean;
  question: string;
  setQuestion: (value: string) => void;
  sessionId: string | null;
  sessionStatus: string | null;
  sessionTitle: string;
  refinedQuestion: string;
  selectedMentor: MentorRecommendation | null;
  userName: string;
  isBusy: boolean;
  isActive: boolean;
  canCompose: boolean;
  showRefinedChoices: boolean;
  submitQuestion: () => Promise<void>;
  retryFailedJob: (jobId: string, retryKind: "analysis" | "persona") => Promise<void>;
  sendRefinedQuestion: () => Promise<void>;
  cancelRefinedQuestion: () => Promise<void>;
  chooseMentor: (mentor: MentorRecommendation) => void;
  confirmMentorRequest: () => Promise<void>;
  editRefinedQuestion: () => void;
  completeQuestionEdit: (content: string) => Promise<void>;
};

export function ChatScreen({
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
}: ChatScreenProps) {
  const router = useRouter();
  const messageScrollRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const [showJumpToLatest, setShowJumpToLatest] = useState(false);
  const sendIcon = isActive ? assets.sendActive : assets.sendDisabled;

  useEffect(() => {
    const scrollArea = messageScrollRef.current;
    if (!scrollArea) return;
    if (isNearBottomRef.current) {
      scrollArea.scrollTo({ top: scrollArea.scrollHeight, behavior: "smooth" });
      setShowJumpToLatest(false);
    } else {
      setShowJumpToLatest(true);
    }
  }, [messages]);

  function handleMessageScroll() {
    const scrollArea = messageScrollRef.current;
    if (!scrollArea) return;
    const isNearBottom = scrollArea.scrollHeight - scrollArea.scrollTop - scrollArea.clientHeight < 96;
    isNearBottomRef.current = isNearBottom;
    setShowJumpToLatest(!isNearBottom);
  }

  function scrollToLatest() {
    const scrollArea = messageScrollRef.current;
    if (!scrollArea) return;
    isNearBottomRef.current = true;
    setShowJumpToLatest(false);
    scrollArea.scrollTo({ top: scrollArea.scrollHeight, behavior: "smooth" });
  }

  return (
    <section className="relative flex h-full min-w-0 flex-1 overflow-hidden rounded-2xl border border-[#eeeeee] bg-[#fefefe] text-[#242424] shadow-[0_6px_20px_rgba(68,74,83,0.12)]">
      <div
        className={cn(
          "relative z-10 flex h-full min-h-0 w-full flex-col items-center",
          isNewChat ? "px-0" : "px-4 sm:px-8 lg:px-[clamp(48px,10vw,180px)]",
        )}
      >
        {isNewChat ? (
          <NewChatWelcome
            userName={userName}
            question={question}
            setQuestion={setQuestion}
            isActive={isActive}
            sendIcon={sendIcon}
            onSubmit={submitQuestion}
            disabled={isBusy}
          />
        ) : (
          <div className="flex min-h-0 w-full flex-1 flex-col items-center justify-end">
            <div className="flex min-h-0 w-full flex-1 flex-col gap-7 py-5">
              <ChatTitleBar title={sessionTitle} />
              <div className="relative min-h-0 flex-1">
                <div ref={messageScrollRef} onScroll={handleMessageScroll} className="h-full overflow-y-auto overscroll-contain">
                  <MessageList
                    messages={messages}
                    onMentorSelect={chooseMentor}
                    onConfirmMentorRequest={confirmMentorRequest}
                    onEditorComplete={completeQuestionEdit}
                    refinedQuestion={refinedQuestion}
                    selectedMentor={selectedMentor}
                    sessionId={sessionId}
                    sessionTitle={sessionTitle}
                  onRetryJob={retryFailedJob}
                  isBusy={isBusy}
                  />
                </div>
                {showJumpToLatest ? (
                  <button
                    type="button"
                    onClick={scrollToLatest}
                    aria-label="최신 메시지로 이동"
                    className="absolute bottom-3 right-3 flex size-9 items-center justify-center rounded-full border border-[#e0e0e0] bg-white text-[#585858] shadow-[0_4px_12px_rgba(68,74,83,0.16)]"
                  >
                    <ChevronDown aria-hidden className="size-5" />
                  </button>
                ) : null}
              </div>
            </div>

            <div className="w-full shrink-0 bg-[linear-gradient(180deg,rgba(254,254,254,0)_0%,#fefefe_12%,#fefefe_88%,rgba(254,254,254,0)_100%)] pb-[calc(96px+env(safe-area-inset-bottom))] pt-5 lg:pb-[96px]">
              {showRefinedChoices ? (
                <RefinedQuestionChoices
                  className="mb-[-28px]"
                  onSend={sendRefinedQuestion}
                  onEdit={editRefinedQuestion}
                  onCancel={cancelRefinedQuestion}
                />
              ) : null}
              <ChatComposer
                question={question}
                setQuestion={setQuestion}
                isActive={isActive}
                sendIcon={sendIcon}
                onSubmit={submitQuestion}
                disabled={isBusy || !canCompose}
                placeholder={composerPlaceholder(sessionStatus, isBusy)}
              />
            </div>
          </div>
        )}

        <div className="contents">
          <button
            type="button"
            aria-label="새 대화"
            onClick={() => router.push(`/chat?new=${Date.now()}`)}
            className="!fixed !bottom-[calc(88px+env(safe-area-inset-bottom))] !right-4 !z-30 flex size-11 items-center justify-center rounded-full bg-[#ffd60a] shadow-[0_6px_20px_rgba(68,74,83,0.24)] lg:hidden"
          >
            <Image src={assets.writeNew} alt="" width={20} height={20} draggable={false} />
          </button>
          <ServiceBottomNavigation className="!fixed !bottom-[calc(16px+env(safe-area-inset-bottom))] !left-1/2 !z-30 !m-0 !-translate-x-1/2 sm:!bottom-6" />
        </div>
      </div>
    </section>
  );
}

function NewChatWelcome({
  userName,
  question,
  setQuestion,
  isActive,
  sendIcon,
  onSubmit,
  disabled,
}: {
  userName: string;
  question: string;
  setQuestion: (value: string) => void;
  isActive: boolean;
  sendIcon: string;
  onSubmit: () => void;
  disabled: boolean;
}) {
  return (
    <div className="relative flex min-h-0 w-full flex-1 overflow-hidden">
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
        <Image src={assets.backgroundLeft} alt="" width={1023} height={1719} className="absolute -left-[520px] top-[-80px] max-w-none opacity-75" draggable={false} />
        <Image src={assets.backgroundBottom} alt="" width={1957} height={1496} className="absolute -left-[260px] top-[52%] max-w-none opacity-75" draggable={false} />
        <Image src={assets.backgroundCenter} alt="" width={1267} height={1204} className="absolute left-[44%] top-[56%] max-w-none opacity-75" draggable={false} />
        <Image src={assets.backgroundRight} alt="" width={1296} height={1015} className="absolute left-[58%] top-[58%] max-w-none opacity-70" draggable={false} />
      </div>

      <div className="relative z-10 flex min-h-0 w-full flex-1 flex-col items-center px-[clamp(24px,4.2vw,60px)] py-[clamp(56px,7vw,100px)]">
        <div className="flex min-h-0 w-full flex-1 items-center justify-center">
          <h1 className="text-center text-[24px] font-extrabold leading-[1.6] text-[#242424] sm:text-[28px]">
            {userName}님 반가워요
            <br />
            막막한 고민을 질문으로 바꿔보세요
          </h1>
        </div>
        <ChatComposer
          className="w-full max-w-[574px]"
          question={question}
          setQuestion={setQuestion}
          isActive={isActive}
          sendIcon={sendIcon}
          onSubmit={onSubmit}
          disabled={disabled}
        />
      </div>
    </div>
  );
}

function ChatTitleBar({ title }: { title: string }) {
  return (
    <header className="flex h-8 w-full shrink-0 items-center justify-center">
      <h1 className="min-w-0 truncate text-center text-[17px] font-semibold leading-[1.55]">{title}</h1>
    </header>
  );
}

function MessageList({
  messages,
  onMentorSelect,
  onConfirmMentorRequest,
  onEditorComplete,
  refinedQuestion,
  selectedMentor,
  sessionId,
  sessionTitle,
  onRetryJob,
  isBusy,
}: {
  messages: ChatMessage[];
  onMentorSelect: (mentor: MentorRecommendation) => void;
  onConfirmMentorRequest: () => void;
  onEditorComplete: (content: string) => void;
  refinedQuestion: string;
  selectedMentor: MentorRecommendation | null;
  sessionId: string | null;
  sessionTitle: string;
  onRetryJob: (jobId: string, retryKind: "analysis" | "persona") => void;
  isBusy: boolean;
}) {
  return (
    <div className="flex w-full flex-col gap-2 pb-4 text-[15px] font-medium leading-[1.6]">
      {messages.map((message) => (
        <MessageRenderer
          key={message.id}
          message={message}
          onMentorSelect={onMentorSelect}
          onConfirmMentorRequest={onConfirmMentorRequest}
          onEditorComplete={onEditorComplete}
          refinedQuestion={refinedQuestion}
          selectedMentor={selectedMentor}
          sessionId={sessionId}
          sessionTitle={sessionTitle}
          onRetryJob={onRetryJob}
          isBusy={isBusy}
        />
      ))}
    </div>
  );
}

function MessageRenderer({
  message,
  onMentorSelect,
  onConfirmMentorRequest,
  onEditorComplete,
  refinedQuestion,
  selectedMentor,
  sessionId,
  sessionTitle,
  onRetryJob,
  isBusy,
}: {
  message: ChatMessage;
  onMentorSelect: (mentor: MentorRecommendation) => void;
  onConfirmMentorRequest: () => void;
  onEditorComplete: (content: string) => void;
  refinedQuestion: string;
  selectedMentor: MentorRecommendation | null;
  sessionId: string | null;
  sessionTitle: string;
  onRetryJob: (jobId: string, retryKind: "analysis" | "persona") => void;
  isBusy: boolean;
}) {
  if (message.role === "user") {
    return <UserMessage compact={message.compact}>{message.text}</UserMessage>;
  }
  if (message.kind === "refined_question") {
    return <RefinedQuestionMessage question={message.text ?? refinedQuestion} title={sessionTitle} />;
  }
  if (message.kind === "mentor_recommendations") {
    return <MentorRecommendationsMessage mentors={message.mentors ?? []} selectedPersonaId={selectedMentor?.personaId ?? null} disabled={isBusy || Boolean(selectedMentor)} onSelect={onMentorSelect} />;
  }
  if (message.kind === "mentor_confirmation") {
    return (
      <MentorConfirmationMessage
        mentorName={selectedMentor?.displayName ?? "선택한 멘토"}
        question={refinedQuestion}
        onConfirm={onConfirmMentorRequest}
        disabled={isBusy}
      />
    );
  }
  if (message.kind === "mentor_request_status") {
    return <MentorRequestStatus text={message.text ?? ""} progress={message.progress} />;
  }
  if (message.kind === "mentor_request_editor") {
    return <MentorRequestEditor initialValue={refinedQuestion} title={sessionTitle} onComplete={onEditorComplete} />;
  }
  if (message.kind === "answer_feedback" && message.answerId && sessionId) {
    return <AnswerFeedbackMessage sessionId={sessionId} answerId={message.answerId} initialStep={message.feedbackStep ?? "rating"} />;
  }
  if (message.kind === "job_retry" && message.jobId && message.retryKind) {
    return (
      <JobRetryMessage
        text={message.text ?? "작업에 실패했습니다."}
        disabled={isBusy}
        onRetry={() => onRetryJob(message.jobId as string, message.retryKind as "analysis" | "persona")}
      />
    );
  }
  return <AssistantBlock><MarkdownMessage text={message.text ?? ""} /></AssistantBlock>;
}

function RefinedQuestionMessage({ question, title }: { question: string; title: string }) {
  return (
    <div className="w-full">
      <p className="text-[14px] font-normal leading-none text-[#9e9e9e]">멘토에게 보낼 질문</p>
      <section className="mt-1.5 w-full max-w-[600px] rounded-2xl border border-[#e0e0e0] bg-white px-6 py-5 shadow-[0_6px_10px_rgba(68,74,83,0.12)]">
        <div className="flex items-center gap-2 px-1">
          <Image src={assets.chat} alt="" width={20} height={20} draggable={false} />
          <h2 className="text-[16px] font-medium leading-[1.6] text-black">{title}</h2>
        </div>
        <div className="mt-2 rounded-3xl bg-[#f7f7f7] px-6 py-5 text-[16px] font-medium leading-[1.6] text-[#585858]">
          {question}
        </div>
      </section>
      <p className="mt-3 text-[16px] font-medium leading-[1.6] text-[#101010]">대화한 내용을 바탕으로 글을 다듬어봤어요.</p>
    </div>
  );
}

function RefinedQuestionChoices({
  className,
  onSend,
  onEdit,
  onCancel,
}: {
  className?: string;
  onSend: () => void;
  onEdit: () => void;
  onCancel: () => void;
}) {
  return (
    <section className={cn("relative w-full rounded-2xl border border-[#eeeeee] bg-white px-5 pb-10 pt-5 shadow-[0_6px_10px_rgba(68,74,83,0.12)]", className)}>
      <p className="text-[16px] font-medium leading-[1.6] text-[#101010]">이 글로 커피챗을 요청할까요?</p>
      <div className="mt-2 flex w-full flex-col gap-1.5">
        <ChoiceRow index={1} label="이 질문으로 보내기" onClick={onSend} active />
        <ChoiceRow index={2} label="질문 수정하기" onClick={onEdit} />
        <ChoiceRow index={3} label="취소하기" onClick={onCancel} />
      </div>
    </section>
  );
}

function ChoiceRow({ index, label, onClick, active = false }: { index: number; label: string; onClick: () => void; active?: boolean }) {
  return (
    <button type="button" onClick={onClick} className={cn("flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition", active ? "bg-[#f7f7f7]" : "hover:bg-[#f7f7f7]")}>
      <span className={cn("flex size-5 shrink-0 items-center justify-center rounded-xl text-[14px] font-medium leading-[1.4] text-white", active ? "bg-[#585858]" : "bg-[#9e9e9e]")}>{index}</span>
      <span className={cn("min-w-0 flex-1 text-[16px] font-medium leading-[1.6]", active ? "text-[#242424]" : "text-[#585858]")}>{label}</span>
    </button>
  );
}

const mentorColors = ["#ffddb3", "#efc4ad", "#ecdfa5"];
const mentorGradients = [
  "radial-gradient(75% 34% at 50% 0%, rgba(255,221,179,0.5) 0%, rgba(255,255,255,0) 100%)",
  "radial-gradient(75% 34% at 50% 0%, rgba(239,196,173,0.5) 0%, rgba(255,255,255,0) 100%)",
  "radial-gradient(75% 34% at 50% 0%, rgba(236,223,165,0.5) 0%, rgba(255,255,255,0) 100%)",
];

function MentorRecommendationsMessage({ mentors, selectedPersonaId, disabled, onSelect }: { mentors: MentorRecommendation[]; selectedPersonaId: string | null; disabled: boolean; onSelect: (mentor: MentorRecommendation) => void }) {
  return (
    <AssistantBlock>
      <div className="text-[15px] font-medium leading-[1.6] text-[#101010]">
        <p>질문의 의도와 막힌 지점을 기준으로 잘 맞는 AI 멘토를 찾았어요.</p>
        <p className="mt-5">원하는 멘토를 직접 선택해 주세요.</p>
      </div>
      <div className="-mx-4 mt-2 flex max-w-[calc(100%+2rem)] snap-x gap-3 overflow-x-auto px-4 pb-5 sm:mx-0 sm:max-w-full sm:flex-wrap sm:px-0">
        {mentors.map((mentor, index) => {
          const tags = Array.isArray(mentor.expertise) ? mentor.expertise : Object.keys(mentor.expertise ?? {});
          return (
            <button
              key={mentor.personaId}
              type="button"
              onClick={() => onSelect(mentor)}
              disabled={disabled}
              className={cn("flex h-[240px] w-[min(78vw,220px)] shrink-0 snap-start flex-col gap-4 rounded-2xl border bg-white px-4 py-5 text-left shadow-[0_16px_12px_rgba(94,107,127,0.16)] transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ffa600] disabled:cursor-default sm:w-[200px]", selectedPersonaId === mentor.personaId ? "border-[#ffd60a] ring-2 ring-[#ffd60a]" : "border-[#eeeeee] enabled:hover:border-[#ffd60a]", disabled && selectedPersonaId !== mentor.personaId && "opacity-55")}
              style={{ backgroundImage: mentorGradients[index % mentorGradients.length] }}
            >
              <span className="flex flex-col gap-2">
                <span className="flex size-10 items-center justify-center rounded-full" style={{ backgroundColor: mentorColors[index % mentorColors.length] }}>
                  <Image src={assets.avatar} alt="" width={14} height={16} draggable={false} />
                </span>
                <span className="flex flex-col">
                  <span className="text-[15px] font-medium leading-[1.7] text-[#242424]">{mentor.displayName}</span>
                  <span className="text-[14px] font-normal leading-none text-[#585858]">{mentor.currentRole} · {mentor.yearsOfExperience}년</span>
                </span>
              </span>
              <span className="flex h-[90px] flex-wrap content-start gap-x-1.5 gap-y-1">
                {tags.slice(0, 4).map((tag) => <span key={tag} className="rounded-lg bg-[#eeeeee] px-2 py-1 text-[13px] font-medium leading-none text-[#585858]">{tag}</span>)}
              </span>
            </button>
          );
        })}
      </div>
      <p className="mt-3 text-[13px] text-[#9e9e9e]">추천 멘토는 실제 인물이 아닌 AI 페르소나입니다.</p>
    </AssistantBlock>
  );
}

function MentorConfirmationMessage({ mentorName, question, onConfirm, disabled }: { mentorName: string; question: string; onConfirm: () => void; disabled: boolean }) {
  return (
    <AssistantBlock>
      <p>{mentorName} AI 멘토에게 아래 질문을 보낼까요?</p>
      <div className="mt-4 max-w-[640px] rounded-3xl bg-[#f7f7f7] px-6 py-5 text-[15px] font-medium leading-[1.6] text-[#585858]">{question}</div>
      <div className="mt-3 flex flex-wrap gap-2">
        <FlowActionButton onClick={onConfirm} emphasis disabled={disabled}>질문 보내기</FlowActionButton>
      </div>
      <p className="mt-2 text-[13px] text-[#9e9e9e]">멘토를 선택한 뒤에는 질문을 수정할 수 없어요.</p>
    </AssistantBlock>
  );
}

function FlowActionButton({ children, onClick, emphasis = false, disabled = false }: { children: ReactNode; onClick: () => void; emphasis?: boolean; disabled?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} className={cn("rounded-[28px] px-4 py-2 text-[14px] font-semibold leading-[1.45] transition disabled:cursor-not-allowed disabled:opacity-50", emphasis ? "bg-[#ffd60a] text-[#242424] shadow-[0_2px_2px_rgba(25,33,61,0.08)]" : "bg-[#eeeeee] text-[#585858] hover:bg-[#e6e6e6]")}>
      {children}
    </button>
  );
}

function AnswerFeedbackMessage({ sessionId, answerId, initialStep }: { sessionId: string; answerId: string; initialStep: "rating" | "consent" | "done" }) {
  const [step, setStep] = useState<"rating" | "consent" | "done" | "error">(initialStep);
  const [failedStep, setFailedStep] = useState<"rating" | "consent">("rating");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorText, setErrorText] = useState("");

  async function submitRating(rating: number) {
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      await apiRequest(`consultations/${sessionId}/feedback`, jsonRequest("POST", { answerId, rating }));
      setStep("consent");
      notifyConsultationsChanged();
    } catch (requestError) {
      setErrorText(requestError instanceof Error ? requestError.message : "요청을 처리하지 못했습니다.");
      setFailedStep("rating");
      setStep("error");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function submitConsent(consent: boolean) {
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      const result = await apiRequest<{ consent: boolean; jobId?: string }>(`consultations/${sessionId}/reuse-consent`, jsonRequest("PUT", { answerId, consent }));
      if (result.jobId) await waitForJob(result.jobId);
      await apiRequest(`consultations/${sessionId}/complete`, { method: "POST" });
      setStep("done");
      notifyConsultationsChanged();
    } catch (requestError) {
      setErrorText(requestError instanceof Error ? requestError.message : "요청을 처리하지 못했습니다.");
      setFailedStep("consent");
      setStep("error");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (step === "rating") {
    return (
      <AssistantBlock>
        <p>이 답변이 도움이 되었나요?</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {[1, 2, 3, 4, 5].map((rating) => <FlowActionButton key={rating} onClick={() => submitRating(rating)} emphasis={rating >= 4} disabled={isSubmitting}>{rating}점</FlowActionButton>)}
          {isSubmitting ? <span className="text-[13px] text-[#9e9e9e]">처리 중...</span> : null}
        </div>
      </AssistantBlock>
    );
  }
  if (step === "consent") {
    return (
      <AssistantBlock>
        <p>이 답변을 익명 처리해서 다른 멘티에게도 재사용해도 될까요?</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <FlowActionButton onClick={() => submitConsent(true)} emphasis disabled={isSubmitting}>동의할게요</FlowActionButton>
          <FlowActionButton onClick={() => submitConsent(false)} disabled={isSubmitting}>아니요, 괜찮아요</FlowActionButton>
          {isSubmitting ? <span className="text-[13px] text-[#9e9e9e]">처리 중이에요...</span> : null}
        </div>
      </AssistantBlock>
    );
  }
  if (step === "error") {
    return (
      <AssistantBlock>
        <p className="text-[#c0392b]">{errorText}</p>
        <div className="mt-3"><FlowActionButton onClick={() => setStep(failedStep)}>다시 시도</FlowActionButton></div>
      </AssistantBlock>
    );
  }
  return <AssistantBlock><p className="text-[#9e9e9e]">소중한 의견 감사합니다. 새로운 상담은 사이드바에서 시작할 수 있어요.</p></AssistantBlock>;
}

function JobRetryMessage({ text, onRetry, disabled }: { text: string; onRetry: () => void; disabled: boolean }) {
  return (
    <AssistantBlock>
      <p className="text-[#c0392b]">{text}</p>
      <div className="mt-3"><FlowActionButton onClick={onRetry} emphasis disabled={disabled}>다시 시도</FlowActionButton></div>
    </AssistantBlock>
  );
}

function MentorRequestStatus({ text, progress }: { text: string; progress?: number }) {
  const normalizedProgress = Math.min(100, Math.max(0, progress ?? 0));
  const isComplete = normalizedProgress >= 100;
  return (
    <AssistantBlock>
      <div className="flex max-w-[480px] items-center gap-2 text-[15px] text-[#585858]">
        {isComplete ? (
          <CheckCircle2 aria-hidden className="size-4 shrink-0 text-[#9a6500]" />
        ) : (
          <LoaderCircle aria-hidden className="size-4 shrink-0 animate-spin text-[#ffa600]" />
        )}
        <p>{text}</p>
      </div>
      {typeof progress === "number" ? (
        <div
          role="progressbar"
          aria-label="작업 진행률"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={normalizedProgress}
          className="mt-2 h-1.5 w-full max-w-[480px] overflow-hidden rounded-full bg-[#eeeeee]"
        >
          <div className="h-full rounded-full bg-[#ffd60a] transition-[width] duration-300" style={{ width: `${normalizedProgress}%` }} />
        </div>
      ) : null}
    </AssistantBlock>
  );
}

function UserMessage({ children, compact = false }: { children: ReactNode; compact?: boolean }) {
  return (
    <div className="flex w-full flex-col items-end">
      <div className={cn("max-w-[600px] whitespace-pre-wrap rounded-[28px] bg-[#eeeeee] px-5 py-3 text-[#101010]", compact && "px-5 py-2")}>{children}</div>
      <div className="h-7" />
    </div>
  );
}

function AssistantBlock({ children }: { children: ReactNode }) {
  return <div className="flex w-full flex-col items-start gap-1"><div className="w-full text-[#242424]">{children}</div></div>;
}

function MarkdownMessage({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-2 whitespace-pre-wrap last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>,
        li: ({ children }) => <li className="pl-0.5">{children}</li>,
        strong: ({ children }) => <strong className="font-bold text-[#101010]">{children}</strong>,
        a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer" className="text-[#9a6500] underline underline-offset-2">{children}</a>,
        code: ({ children }) => <code className="rounded bg-[#f2f2f2] px-1 py-0.5 text-[0.92em]">{children}</code>,
      }}
    >
      {text}
    </ReactMarkdown>
  );
}

function MentorRequestEditor({ initialValue, title, onComplete }: { initialValue: string; title: string; onComplete: (content: string) => void }) {
  const [content, setContent] = useState(initialValue);
  return (
    <div className="flex h-full w-full flex-col gap-2 pb-4">
      <p className="text-[14px] font-normal leading-none text-[#9e9e9e]">질문 직접 수정하기</p>
      <section className="w-full rounded-2xl border border-[#e0e0e0] bg-white px-6 py-5 shadow-[0_6px_10px_rgba(68,74,83,0.12)]">
        <div className="flex items-center gap-2 px-1">
          <Image src={assets.editLine} alt="" width={20} height={20} draggable={false} />
          <h2 className="text-[15px] font-medium leading-[1.6] text-black">{title}</h2>
        </div>
        <textarea value={content} onChange={(event) => setContent(event.target.value)} className="mt-2 min-h-36 w-full resize-y rounded-3xl border-0 bg-[#f7f7f7] px-6 py-5 text-[15px] font-medium leading-[1.6] text-[#585858] outline-none focus:ring-2 focus:ring-[#ffd60a]" />
        <div className="mt-2 flex justify-end">
          <button type="button" onClick={() => onComplete(content)} disabled={content.trim().length < 10} className="rounded-lg bg-[#eeeeee] px-3 py-2 text-[14px] font-semibold leading-[1.4] text-[#242424] disabled:opacity-50">수정완료</button>
        </div>
      </section>
    </div>
  );
}

function composerPlaceholder(sessionStatus: string | null, isBusy: boolean) {
  if (isBusy) return "요청을 처리하고 있어요...";
  if (sessionStatus === "awaiting_confirmation") return "정리된 질문을 확인해 주세요.";
  if (sessionStatus === "analyzing") return "질문을 분석하고 있어요...";
  if (sessionStatus === "persona_recommended") return "위에서 AI 멘토를 선택해 주세요.";
  if (sessionStatus === "persona_answer_generating") return "AI 멘토가 답변을 작성하고 있어요...";
  if (["ai_answered", "persona_answered", "awaiting_feedback"].includes(sessionStatus ?? "")) {
    return "답변을 확인하고 평가해 주세요.";
  }
  if (["assetizing", "assetized", "completed"].includes(sessionStatus ?? "")) {
    return "완료된 상담입니다.";
  }
  if (sessionStatus === "failed") return "작업을 다시 시도해 주세요.";
  return "무엇이 궁금하신가요?";
}

function ChatComposer({ className, question, setQuestion, isActive, sendIcon, onSubmit, disabled = false, placeholder = "무엇이 궁금하신가요?" }: { className?: string; question: string; setQuestion: (value: string) => void; isActive: boolean; sendIcon: string; onSubmit: () => void; disabled?: boolean; placeholder?: string }) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 160)}px`;
  }, [question]);

  return (
    <form className={cn("relative z-10 w-full rounded-2xl border border-[#eeeeee] bg-white px-6 pb-4 pt-6 shadow-[0_6px_10px_rgba(68,74,83,0.12)]", className)} onSubmit={(event) => { event.preventDefault(); onSubmit(); }}>
      <textarea
        ref={textareaRef}
        value={question}
        disabled={disabled}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder={placeholder}
        rows={1}
        className="block max-h-40 min-h-[24px] w-full resize-none overflow-y-auto border-0 bg-transparent text-[15px] font-medium leading-[1.6] text-[#242424] outline-none placeholder:text-[#9e9e9e]"
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSubmit();
          }
        }}
      />
      <div className="mt-3 h-px w-full bg-[#eeeeee]" />
      <div className="mt-4 flex items-center justify-end">
        <button type="submit" aria-label="질문 보내기" disabled={!isActive || disabled} className={cn("flex size-8 items-center justify-center rounded-full p-1.5 shadow-[0_2px_2px_rgba(25,33,61,0.08)]", isActive ? "bg-[#ffd60a]" : "bg-[#ffe66c]")}>
          <Image src={sendIcon} alt="" width={20} height={20} draggable={false} />
        </button>
      </div>
    </form>
  );
}
