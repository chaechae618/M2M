"use client";

import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ServiceBottomNavigation } from "@/widgets/service-bottom-navigation/ServiceBottomNavigation";
import { ApiError, apiRequest, jsonRequest } from "@/shared/api/client";
import type { AuthUser } from "@/shared/api/types";
import { routes } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/cn";

type MessageRole = "user" | "assistant";
type MessageKind =
  | "text"
  | "refined_question"
  | "mentor_recommendations"
  | "mentor_confirmation"
  | "mentor_request_status"
  | "mentor_request_editor";

type ChatMessage = {
  id: string;
  role: MessageRole;
  kind: MessageKind;
  content?: ReactNode;
  text?: string;
  userActions?: boolean;
  compact?: boolean;
  mentors?: MentorRecommendation[];
};

type ApiChatMessage = { id: string; role: MessageRole; content: string; createdAt: string };
type RefinedQuestion = { content: string | null };
type ConsultationSession = { id: string; title: string; status: string; refinedQuestion: string | null; route: string | null };
type MentorRecommendation = {
  personaId: string;
  displayName: string;
  currentRole: string;
  yearsOfExperience: number;
  expertise: string[] | Record<string, unknown>;
  profileSummary: string;
  recommendationReason: string;
  matchScore: number;
};
type Job = { jobId: string; status: string; progress: number; currentStep: string; error?: { message?: string } | null };
type ConsultationResult = {
  status: string;
  route: string | null;
  reason?: string | null;
  answer: { id: string; content: string; summary?: string | null } | null;
};

const assets = {
  avatar: "/figma-assets/chat/avatar-person.svg",
  backgroundBottom: "/figma-assets/chat/bg-ellipse-744.svg",
  backgroundCenter: "/figma-assets/chat/bg-ellipse-743.svg",
  backgroundLeft: "/figma-assets/chat/bg-ellipse-742.svg",
  backgroundRight: "/figma-assets/chat/bg-ellipse-745.svg",
  chat: "/figma-assets/chat/chat.svg",
  editLine: "/figma-assets/chat/edit-line.svg",
  editPencil: "/figma-assets/chat/edit-pencil.svg",
  moreDot: "/figma-assets/chat/more-dot.svg",
  plus: "/figma-assets/chat/plus.svg",
  sendActive: "/figma-assets/chat/send-active.svg",
  sendDisabled: "/figma-assets/chat/send-disabled.svg",
  writeNew: "/figma-assets/chat/write-new.svg",
};

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="h-full w-full bg-white" />}>
      <ChatPageContent />
    </Suspense>
  );
}

function ChatPageContent() {
  const searchParams = useSearchParams();
  const newChatToken = searchParams.get("new");

  return <ChatSession key={newChatToken ?? "current-chat"} startsAsNewChat />;
}

function ChatSession({ startsAsNewChat }: { startsAsNewChat: boolean }) {
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isNewChat, setIsNewChat] = useState(startsAsNewChat);
  const [question, setQuestion] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionTitle, setSessionTitle] = useState("새 상담");
  const [refinedQuestion, setRefinedQuestion] = useState("");
  const [selectedMentor, setSelectedMentor] = useState<MentorRecommendation | null>(null);
  const [userName, setUserName] = useState("이름");
  const [isBusy, setIsBusy] = useState(false);
  const isActive = question.trim().length > 0;
  const sendIcon = useMemo(() => (isActive ? assets.sendActive : assets.sendDisabled), [isActive]);
  const lastMessage = messages[messages.length - 1];
  const showRefinedChoices = lastMessage?.kind === "refined_question";
  const showMentorRecommendations = lastMessage?.kind === "mentor_recommendations";
  const visibleMessages = showRefinedChoices ? messages.slice(-1) : showMentorRecommendations ? messages.slice(-2) : messages;
  const messageScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiRequest<AuthUser>("auth/me")
      .then((user) => setUserName(user.name))
      .catch((requestError) => {
        if (requestError instanceof ApiError && requestError.status === 401) router.replace(routes.login);
      });
  }, [router]);

  useEffect(() => {
    const scrollArea = messageScrollRef.current;

    if (!scrollArea) {
      return;
    }

    scrollArea.scrollTop = scrollArea.scrollHeight;
  }, [messages]);

  function appendMessages(nextMessages: ChatMessage[]) {
    setMessages((current) => {
      const withoutEditor = current.filter((message) => message.kind !== "mentor_request_editor");
      return [...withoutEditor, ...nextMessages];
    });
  }

  function appendError(requestError: unknown) {
    appendMessages([{ id: `a-error-${Date.now()}`, role: "assistant", kind: "text", text: requestError instanceof Error ? requestError.message : "요청을 처리하지 못했습니다." }]);
  }

  function apiMessage(message: ApiChatMessage): ChatMessage {
    return { id: message.id, role: message.role, kind: "text", text: message.content };
  }

  async function handleSubmit() {
    const content = question.trim();
    if (!content || isBusy) {
      return;
    }

    if (!sessionId && content.length < 10) {
      appendMessages([{ id: `a-short-${Date.now()}`, role: "assistant", kind: "text", text: "고민을 조금만 더 자세히 적어주세요. 첫 질문은 10자 이상이어야 해요." }]);
      return;
    }

    const userMessage: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      kind: "text",
      text: content,
    };

    setQuestion("");
    setIsNewChat(false);
    appendMessages([userMessage]);
    setIsBusy(true);
    try {
      if (!sessionId) {
        const created = await apiRequest<{ session: ConsultationSession; assistantMessage: ApiChatMessage }>("consultations", jsonRequest("POST", { initialMessage: content }));
        setSessionId(created.session.id);
        setSessionTitle(created.session.title);
        if (created.session.refinedQuestion) {
          setRefinedQuestion(created.session.refinedQuestion);
          appendMessages([{ id: `a-refined-${Date.now()}`, role: "assistant", kind: "refined_question", text: created.session.refinedQuestion }]);
        } else {
          appendMessages([apiMessage(created.assistantMessage)]);
        }
      } else {
        const result = await apiRequest<{ sessionStatus: string; needMoreInfo: boolean; assistantMessage: ApiChatMessage | null; refinedQuestion: RefinedQuestion | null }>(`consultations/${sessionId}/messages`, jsonRequest("POST", { content }));
        if (result.refinedQuestion?.content) {
          setRefinedQuestion(result.refinedQuestion.content);
          appendMessages([{ id: `a-refined-${Date.now()}`, role: "assistant", kind: "refined_question", text: result.refinedQuestion.content }]);
        } else if (result.assistantMessage) {
          appendMessages([apiMessage(result.assistantMessage)]);
        }
      }
    } catch (requestError) {
      appendError(requestError);
    } finally {
      setIsBusy(false);
    }
  }

  async function waitForJob(jobId: string) {
    for (let attempt = 0; attempt < 90; attempt += 1) {
      const job = await apiRequest<Job>(`jobs/${jobId}`);
      if (job.status === "completed") return;
      if (job.status === "failed") throw new Error(job.error?.message ?? "답변 생성 작업에 실패했습니다.");
      await new Promise((resolve) => setTimeout(resolve, 800));
    }
    throw new Error("답변 생성 시간이 길어지고 있습니다. 잠시 후 다시 시도해주세요.");
  }

  async function handleSendRefinedQuestion() {
    if (!sessionId || isBusy) return;
    appendMessages([
      {
        id: `u-refined-send-${Date.now()}`,
        role: "user",
        kind: "text",
        compact: true,
        text: "이 질문으로 보내기",
      },
      { id: `a-analyzing-${Date.now()}`, role: "assistant", kind: "mentor_request_status", text: "질문을 분석하고 있어요" },
    ]);
    setIsBusy(true);
    try {
      const confirmation = await apiRequest<{ jobId: string }>(`consultations/${sessionId}/confirm`, { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() } });
      await waitForJob(confirmation.jobId);
      const result = await apiRequest<ConsultationResult>(`consultations/${sessionId}/result`);
      if (result.route === "llm_direct" && result.answer) {
        appendMessages([{ id: `a-answer-${Date.now()}`, role: "assistant", kind: "text", text: result.answer.content }]);
      } else {
        const recommendations = await apiRequest<{ personas: MentorRecommendation[] }>(`consultations/${sessionId}/persona-recommendations`);
        appendMessages([{ id: `a-mentors-${Date.now()}`, role: "assistant", kind: "mentor_recommendations", mentors: recommendations.personas }]);
      }
    } catch (requestError) {
      appendError(requestError);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCancelRefinedQuestion() {
    if (!sessionId) return;
    try {
      await apiRequest(`consultations/${sessionId}`, { method: "DELETE" });
    } catch (requestError) {
      appendError(requestError);
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
        text: "좋아요. 더 이야기하면서 질문을 다듬어도 되고, 준비되면 다시 멘토에게 보낼 수 있어요.",
      },
    ]);
    setSessionId(null);
    setRefinedQuestion("");
    setSelectedMentor(null);
  }

  function handleMentorSelect(mentor: MentorRecommendation) {
    setSelectedMentor(mentor);
    appendMessages([
      {
        id: `u-mentor-select-${Date.now()}`,
        role: "user",
        kind: "text",
        compact: true,
        text: `${mentor.displayName} 멘토를 선택할게`,
      },
      {
        id: `a-mentor-confirm-${Date.now()}`,
        role: "assistant",
        kind: "mentor_confirmation",
      },
    ]);
  }

  async function handleConfirmMentorRequest() {
    if (!sessionId || !selectedMentor || isBusy) return;
    appendMessages([
      {
        id: `u-mentor-confirm-${Date.now()}`,
        role: "user",
        kind: "text",
        compact: true,
        text: "질문 보내기",
      },
      {
        id: `a-status-${Date.now()}`,
        role: "assistant",
        kind: "mentor_request_status",
        text: "선택한 AI 멘토가 답변을 작성하고 있어요",
      },
    ]);
    setIsBusy(true);
    try {
      const selection = await apiRequest<{ jobId: string }>(`consultations/${sessionId}/persona-selection`, jsonRequest("POST", { personaId: selectedMentor.personaId }));
      await waitForJob(selection.jobId);
      const result = await apiRequest<ConsultationResult>(`consultations/${sessionId}/result`);
      if (!result.answer) throw new Error("생성된 답변을 찾지 못했습니다.");
      appendMessages([{ id: `a-persona-answer-${Date.now()}`, role: "assistant", kind: "text", text: result.answer.content }]);
    } catch (requestError) {
      appendError(requestError);
    } finally {
      setIsBusy(false);
    }
  }

  function handleEditRequest() {
    appendMessages([
      {
        id: `editor-${Date.now()}`,
        role: "assistant",
        kind: "mentor_request_editor",
      },
    ]);
  }

  async function handleEditorComplete(content: string) {
    if (!sessionId || content.trim().length < 10) return;
    setIsBusy(true);
    try {
      const result = await apiRequest<{ refinedQuestion: RefinedQuestion }>(`consultations/${sessionId}/refined-question`, jsonRequest("PATCH", { content: content.trim() }));
      const nextQuestion = result.refinedQuestion.content ?? content.trim();
      setRefinedQuestion(nextQuestion);
      setMessages((current) => [
        ...current.filter((message) => message.kind !== "mentor_request_editor"),
        { id: `u-edit-complete-${Date.now()}`, role: "user", kind: "text", compact: true, text: "수정완료" },
        { id: `a-refined-again-${Date.now()}`, role: "assistant", kind: "refined_question", text: nextQuestion },
      ]);
    } catch (requestError) {
      appendError(requestError);
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="relative flex h-full min-w-0 flex-1 overflow-hidden rounded-2xl border border-[#eeeeee] bg-[#fefefe] text-[#242424] shadow-[0_6px_20px_rgba(68,74,83,0.12)]">
      <div className={cn("relative z-10 flex h-full min-h-0 w-full flex-col items-center", isNewChat ? "px-0" : "px-[clamp(24px,12.5vw,180px)]")}>
        {isNewChat ? (
          <NewChatWelcome
            userName={userName}
            question={question}
            setQuestion={setQuestion}
            isActive={isActive}
            sendIcon={sendIcon}
            onSubmit={handleSubmit}
            disabled={isBusy}
          />
        ) : (
          <div className="flex min-h-0 w-full flex-1 flex-col items-center justify-end">
            <div className="flex min-h-0 w-full flex-1 flex-col gap-7 py-5">
              <ChatTitleBar title={sessionTitle} />

              <div ref={messageScrollRef} className="min-h-0 flex-1 overflow-y-auto">
                <MessageList
                  messages={visibleMessages}
                  onMentorSelect={handleMentorSelect}
                  onConfirmMentorRequest={handleConfirmMentorRequest}
                  onEditRequest={handleEditRequest}
                  onEditorComplete={handleEditorComplete}
                  refinedQuestion={refinedQuestion}
                  selectedMentor={selectedMentor}
                />
              </div>
            </div>

            <div className="w-full shrink-0 bg-[linear-gradient(180deg,rgba(254,254,254,0)_0%,#fefefe_12%,#fefefe_88%,rgba(254,254,254,0)_100%)] py-5">
              {showRefinedChoices ? (
                <RefinedQuestionChoices
                  className="mb-[-28px]"
                  onSend={handleSendRefinedQuestion}
                  onEdit={handleEditRequest}
                  onCancel={handleCancelRefinedQuestion}
                />
              ) : null}
              <ChatComposer
                question={question}
                setQuestion={setQuestion}
                isActive={isActive}
                sendIcon={sendIcon}
                onSubmit={handleSubmit}
                disabled={isBusy}
              />
            </div>
          </div>
        )}

        <div className="shrink-0 pb-6 pt-3">
          <ServiceBottomNavigation className="!fixed !bottom-6 !left-1/2 !z-30 !m-0 !-translate-x-1/2" />
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
    <header className="grid h-8 w-full shrink-0 grid-cols-[20px_minmax(0,1fr)_20px] items-center">
      <span aria-hidden="true" />
      <h1 className="min-w-0 truncate text-center text-[17px] font-semibold leading-[1.55]">{title}</h1>
      <button type="button" aria-label="더보기" className="flex size-5 items-center justify-center gap-[3px]">
        <Image src={assets.moreDot} alt="" width={20} height={20} draggable={false} />
      </button>
    </header>
  );
}

function MessageList({
  messages,
  onMentorSelect,
  onConfirmMentorRequest,
  onEditRequest,
  onEditorComplete,
  refinedQuestion,
  selectedMentor,
}: {
  messages: ChatMessage[];
  onMentorSelect: (mentor: MentorRecommendation) => void;
  onConfirmMentorRequest: () => void;
  onEditRequest: () => void;
  onEditorComplete: (content: string) => void;
  refinedQuestion: string;
  selectedMentor: MentorRecommendation | null;
}) {
  return (
    <div className="flex w-full flex-col gap-2 pb-4 text-[15px] font-medium leading-[1.6]">
      {messages.map((message) => (
        <MessageRenderer
          key={message.id}
          message={message}
          onMentorSelect={onMentorSelect}
          onConfirmMentorRequest={onConfirmMentorRequest}
          onEditRequest={onEditRequest}
          onEditorComplete={onEditorComplete}
          refinedQuestion={refinedQuestion}
          selectedMentor={selectedMentor}
        />
      ))}
    </div>
  );
}

function MessageRenderer({
  message,
  onMentorSelect,
  onConfirmMentorRequest,
  onEditRequest,
  onEditorComplete,
  refinedQuestion,
  selectedMentor,
}: {
  message: ChatMessage;
  onMentorSelect: (mentor: MentorRecommendation) => void;
  onConfirmMentorRequest: () => void;
  onEditRequest: () => void;
  onEditorComplete: (content: string) => void;
  refinedQuestion: string;
  selectedMentor: MentorRecommendation | null;
}) {
  if (message.role === "user") {
    return (
      <UserMessage actions={message.userActions} compact={message.compact}>
        {message.text}
      </UserMessage>
    );
  }

  if (message.kind === "refined_question") {
    return <RefinedQuestionMessage question={message.text ?? refinedQuestion} />;
  }

  if (message.kind === "mentor_recommendations") {
    return <MentorRecommendationsMessage mentors={message.mentors ?? []} onSelect={onMentorSelect} />;
  }

  if (message.kind === "mentor_confirmation") {
    return <MentorConfirmationMessage mentorName={selectedMentor?.displayName ?? "선택한 멘토"} question={refinedQuestion} onConfirm={onConfirmMentorRequest} onEdit={onEditRequest} />;
  }

  if (message.kind === "mentor_request_status") {
    return <MentorRequestStatus onEditRequest={onEditRequest} text={message.text ?? ""} />;
  }

  if (message.kind === "mentor_request_editor") {
    return <MentorRequestEditor initialValue={refinedQuestion} onComplete={onEditorComplete} />;
  }

  return (
    <AssistantBlock>
      {message.content ?? message.text}
      <MessageActions hidden />
    </AssistantBlock>
  );
}

function RefinedQuestionMessage({ question }: { question: string }) {
  return (
    <div className="w-full">
      <p className="text-[14px] font-normal leading-none text-[#9e9e9e]">멘토에게 보낼 질문</p>
      <section className="mt-1.5 w-full max-w-[600px] rounded-2xl border border-[#e0e0e0] bg-white px-6 py-5 shadow-[0_6px_10px_rgba(68,74,83,0.12)]">
        <div className="flex items-center gap-2 px-1">
          <Image src={assets.chat} alt="" width={20} height={20} draggable={false} />
          <h2 className="text-[16px] font-medium leading-[1.6] text-black">비전공자 PM 직무 준비</h2>
        </div>
        <div className="mt-2 rounded-3xl bg-[#f7f7f7] px-6 py-5 text-[16px] font-medium leading-[1.6] text-[#585858]">
          {question}
        </div>
      </section>
      <div className="mt-3">
        <p className="text-[16px] font-medium leading-[1.6] text-[#101010]">대화한 내용을 바탕으로 글을 다듬어봤어요.</p>
      </div>
      <MessageActions hidden />
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
    <section
      className={cn(
        "relative w-full rounded-2xl border border-[#eeeeee] bg-white px-5 pb-10 pt-5 shadow-[0_6px_10px_rgba(68,74,83,0.12)]",
        className,
      )}
    >
      <p className="text-[16px] font-medium leading-[1.6] text-[#101010]">이 글로 커피챗을 요청할까요?</p>
      <div className="mt-2 flex w-full flex-col gap-1.5">
        <ChoiceRow index={1} label="이 질문으로 보내기" onClick={onSend} active />
        <ChoiceRow index={2} label="질문 수정하기" onClick={onEdit} />
        <ChoiceRow index={3} label="취소하기" onClick={onCancel} />
      </div>
    </section>
  );
}

function ChoiceRow({
  index,
  label,
  onClick,
  active = false,
}: {
  index: number;
  label: string;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition",
        active ? "bg-[#f7f7f7]" : "hover:bg-[#f7f7f7]",
      )}
    >
      <span
        className={cn(
          "flex size-5 shrink-0 items-center justify-center rounded-xl text-[14px] font-medium leading-[1.4] text-white",
          active ? "bg-[#585858]" : "bg-[#9e9e9e]",
        )}
      >
        {index}
      </span>
      <span className={cn("min-w-0 flex-1 text-[16px] font-medium leading-[1.6]", active ? "text-[#242424]" : "text-[#585858]")}>
        {label}
      </span>
    </button>
  );
}

const mentorColors = ["#ffddb3", "#efc4ad", "#ecdfa5"];
const mentorGradients = [
  "radial-gradient(75% 34% at 50% 0%, rgba(255,221,179,0.5) 0%, rgba(255,255,255,0) 100%)",
  "radial-gradient(75% 34% at 50% 0%, rgba(239,196,173,0.5) 0%, rgba(255,255,255,0) 100%)",
  "radial-gradient(75% 34% at 50% 0%, rgba(236,223,165,0.5) 0%, rgba(255,255,255,0) 100%)",
];

function MentorRecommendationsMessage({ mentors, onSelect }: { mentors: MentorRecommendation[]; onSelect: (mentor: MentorRecommendation) => void }) {
  return (
    <AssistantBlock>
      <div className="text-[15px] font-medium leading-[1.6] text-[#101010]">
        <p>
          질문의 의도와 막힌 지점을 기준으로 잘 맞는 AI 멘토를 찾았어요.
          <br />
          추천 결과를 확인한 뒤 원하는 멘토를 직접 선택해 주세요.
        </p>
        <div className="mt-5">
          <p>원하는 멘토를 직접 선택해 주세요.</p>
        </div>
      </div>
      <div className="mt-2 flex max-w-full flex-wrap gap-2">
        {mentors.map((mentor, index) => {
          const tags = Array.isArray(mentor.expertise) ? mentor.expertise : Object.keys(mentor.expertise ?? {});
          return (
          <button
            key={mentor.personaId}
            type="button"
            onClick={() => onSelect(mentor)}
            className="flex h-[240px] w-[200px] flex-col gap-4 rounded-2xl border border-[#eeeeee] bg-white px-4 py-5 text-left shadow-[0_16px_12px_rgba(94,107,127,0.16)] transition hover:border-[#ffd60a] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ffa600]"
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
              {tags.slice(0, 4).map((tag) => (
                <span key={tag} className="rounded-lg bg-[#eeeeee] px-2 py-1 text-[13px] font-medium leading-none text-[#585858]">
                  {tag}
                </span>
              ))}
            </span>
          </button>
          );
        })}
      </div>
      <p className="mt-3 text-[13px] text-[#9e9e9e]">추천 멘토는 실제 인물이 아닌 AI 페르소나입니다.</p>
      <MessageActions />
    </AssistantBlock>
  );
}

function MentorConfirmationMessage({ mentorName, question, onConfirm, onEdit }: { mentorName: string; question: string; onConfirm: () => void; onEdit: () => void }) {
  return (
    <AssistantBlock>
      <p>
        {mentorName} 멘토에게 아래 질문을 보낼까요?
        <br />
        보내기 전에 내용을 한 번 더 수정할 수 있어요.
      </p>
      <div className="mt-4 max-w-[640px] rounded-3xl bg-[#f7f7f7] px-6 py-5 text-[15px] font-medium leading-[1.6] text-[#585858]">
        {question}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <FlowActionButton onClick={onConfirm} emphasis>
          질문 보내기
        </FlowActionButton>
        <FlowActionButton onClick={onEdit}>질문 수정하기</FlowActionButton>
      </div>
      <MessageActions />
    </AssistantBlock>
  );
}

function FlowActionButton({
  children,
  onClick,
  emphasis = false,
}: {
  children: ReactNode;
  onClick: () => void;
  emphasis?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-[28px] px-4 py-2 text-[14px] font-semibold leading-[1.45] transition",
        emphasis
          ? "bg-[#ffd60a] text-[#242424] shadow-[0_2px_2px_rgba(25,33,61,0.08)]"
          : "bg-[#eeeeee] text-[#585858] hover:bg-[#e6e6e6]",
      )}
    >
      {children}
    </button>
  );
}

function MentorRequestStatus({ text, onEditRequest }: { text: string; onEditRequest: () => void }) {
  return (
    <AssistantBlock>
      <button
        type="button"
        onClick={onEditRequest}
        className="bg-[linear-gradient(90deg,#959595_0%,#cacaca_15%,#bbbbbb_33%)] bg-clip-text text-left text-[15px] text-transparent"
      >
        {text}
      </button>
      <MessageActions hidden />
    </AssistantBlock>
  );
}

function UserMessage({
  children,
  actions = false,
  compact = false,
}: {
  children: ReactNode;
  actions?: boolean;
  compact?: boolean;
}) {
  return (
    <div className="flex w-full flex-col items-end">
      <div
        className={cn(
          "max-w-[600px] whitespace-pre-wrap rounded-[28px] bg-[#eeeeee] px-5 py-3 text-[#101010]",
          compact && "px-5 py-2",
        )}
      >
        {children}
      </div>
      <div className="flex h-7 items-center justify-end gap-1">
        {actions ? (
          <>
            <button type="button" aria-label="새로 작성" className="relative flex size-7 items-center justify-center rounded-lg">
              <Image src={assets.writeNew} alt="" width={18} height={18} draggable={false} />
            </button>
            <button type="button" aria-label="수정" className="relative flex size-7 items-center justify-center rounded-lg">
              <Image src={assets.editPencil} alt="" width={18} height={18} draggable={false} />
            </button>
          </>
        ) : null}
      </div>
    </div>
  );
}

function AssistantBlock({ children }: { children: ReactNode }) {
  return (
    <div className="flex w-full flex-col items-start gap-1">
      <div className="w-full text-[#242424]">{children}</div>
    </div>
  );
}

function MessageActions({ hidden = false }: { hidden?: boolean }) {
  return (
    <div className={cn("mt-1 flex h-7 items-center gap-1", hidden && "invisible")}>
      {["복사", "좋아요", "싫어요", "다시 생성"].map((label) => (
        <button key={label} type="button" aria-label={label} className="size-7 rounded-lg" />
      ))}
    </div>
  );
}

function MentorRequestEditor({ initialValue, onComplete }: { initialValue: string; onComplete: (content: string) => void }) {
  const [content, setContent] = useState(initialValue);
  return (
    <div className="flex h-full w-full flex-col gap-2 pb-4">
      <p className="text-[14px] font-normal leading-none text-[#9e9e9e]">질문 직접 수정하기</p>
      <section className="w-full rounded-2xl border border-[#e0e0e0] bg-white px-6 py-5 shadow-[0_6px_10px_rgba(68,74,83,0.12)]">
        <div className="flex items-center gap-2 px-1">
          <Image src={assets.editLine} alt="" width={20} height={20} draggable={false} />
          <h2 className="text-[15px] font-medium leading-[1.6] text-black">비전공자 PM 직무 준비</h2>
        </div>
        <textarea value={content} onChange={(event) => setContent(event.target.value)} className="mt-2 min-h-36 w-full resize-y rounded-3xl border-0 bg-[#f7f7f7] px-6 py-5 text-[15px] font-medium leading-[1.6] text-[#585858] outline-none focus:ring-2 focus:ring-[#ffd60a]" />
        <div className="mt-2 flex justify-end">
          <button
            type="button"
            onClick={() => onComplete(content)}
            disabled={content.trim().length < 10}
            className="rounded-lg bg-[#eeeeee] px-3 py-2 text-[14px] font-semibold leading-[1.4] text-[#242424]"
          >
            수정완료
          </button>
        </div>
      </section>
    </div>
  );
}

function ChatComposer({
  className,
  question,
  setQuestion,
  isActive,
  sendIcon,
  onSubmit,
  disabled = false,
}: {
  className?: string;
  question: string;
  setQuestion: (value: string) => void;
  isActive: boolean;
  sendIcon: string;
  onSubmit: () => void;
  disabled?: boolean;
}) {
  return (
    <form
      className={cn("relative z-10 w-full rounded-2xl border border-[#eeeeee] bg-white px-6 pb-4 pt-6 shadow-[0_6px_10px_rgba(68,74,83,0.12)]", className)}
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <textarea
        value={question}
        disabled={disabled}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder="무엇이 궁금하신가요?"
        rows={1}
        className="block min-h-[24px] w-full resize-none border-0 bg-transparent text-[15px] font-medium leading-[1.6] text-[#242424] outline-none placeholder:text-[#9e9e9e]"
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSubmit();
          }
        }}
      />
      <div className="mt-3 h-px w-full bg-[#eeeeee]" />
      <div className="mt-4 flex items-center justify-between">
        <button type="button" aria-label="첨부 추가" className="relative flex size-5 items-center justify-center">
          <Image src={assets.plus} alt="" width={15} height={15} draggable={false} />
        </button>
        <button
          type="submit"
          aria-label="질문 보내기"
          disabled={!isActive || disabled}
          className={cn(
            "flex size-8 items-center justify-center rounded-full p-1.5 shadow-[0_2px_2px_rgba(25,33,61,0.08)]",
            isActive ? "bg-[#ffd60a]" : "bg-[#ffe66c]",
          )}
        >
          <Image src={sendIcon} alt="" width={20} height={20} draggable={false} />
        </button>
      </div>
    </form>
  );
}
