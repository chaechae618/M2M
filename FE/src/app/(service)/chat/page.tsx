"use client";

import Image from "next/image";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ServiceBottomNavigation } from "@/widgets/service-bottom-navigation/ServiceBottomNavigation";
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
};

const chatTopics = [
  "비전공자도 PM 가능할까?",
  "PM은 개발을 얼마나 알아야 할...",
  "서비스 기획 경험이 부족해요",
  "인턴 지원 전에 포폴 점검",
];

const recentChats = [
  "비전공자 PM 준비",
  "UX 포트폴리오 개선",
  "PM 직무 탐색",
  "마케팅 인턴 준비",
  "서비스 기획 포트폴리오",
  "첫 인턴 지원 고민",
  "데이터 직무 전환",
  "브랜드 마케터 준비",
  "디자인 직무 선택",
  "개발 지식이 필요한가요",
];

const assets = {
  arrowLeft: "/figma-assets/chat/arrow-left.svg",
  avatar: "/figma-assets/chat/avatar-person.svg",
  chat: "/figma-assets/chat/chat.svg",
  editLine: "/figma-assets/chat/edit-line.svg",
  editPencil: "/figma-assets/chat/edit-pencil.svg",
  folder: "/figma-assets/chat/folder.svg",
  moreDot: "/figma-assets/chat/more-dot.svg",
  plus: "/figma-assets/chat/plus.svg",
  searchCircle: "/figma-assets/chat/search-circle.svg",
  searchHandle: "/figma-assets/chat/search-handle.svg",
  sendActive: "/figma-assets/chat/send-active.svg",
  sendDisabled: "/figma-assets/chat/send-disabled.svg",
  sidebarToggle: "/figma-assets/chat/sidebar-toggle.svg",
  writeNew: "/figma-assets/chat/write-new.svg",
};

const initialMessages: ChatMessage[] = [
  {
    id: "u-1",
    role: "user",
    kind: "text",
    text: "마케팅 직무 준비 중인데 포트폴리오에 쓸 게 너무 애매해. 인턴도 없고 공모전 수상도 없어.",
  },
  {
    id: "a-1",
    role: "assistant",
    kind: "text",
    content: (
      <>
        지금 갖고 있는 경험을 먼저 쪼개보면 좋아요.
        <br />
        혹시 직접 운영해본 SNS 계정, 학교 과제에서 만든 캠페인 기획안, 브랜드 분석 자료, 콘텐츠 제작 경험 같은 게 있어요?
      </>
    ),
  },
  {
    id: "u-2",
    role: "user",
    kind: "text",
    userActions: true,
    text: "개인 인스타 계정 3개월 정도 운영한 거 있어. 대학생 자취 생활 팁 올렸고 릴스랑 카드뉴스 섞어서 올렸어. 근데 팔로워가 180명밖에 안 돼.",
  },
  {
    id: "a-2",
    role: "assistant",
    kind: "text",
    content: (
      <>
        <p>
          팔로워 180명이라도 포트폴리오 소재가 될 수 있어요.
          <br />
          다만 “인스타 운영함”으로 쓰면 약하고, “자취 대학생 타깃 콘텐츠 실험”으로 바꿔야 해요.
        </p>
        <p className="mt-5">몇 개 정도 올렸고, 반응이 좋았던 콘텐츠가 있었어요?</p>
      </>
    ),
  },
  {
    id: "u-3",
    role: "user",
    kind: "text",
    text: "릴스 12개, 카드뉴스 8개 정도.\n조회수 4,800 정도 나왔어. 나머지는 300~700 정도.",
  },
  {
    id: "a-3",
    role: "assistant",
    kind: "refined_question",
  },
];

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [question, setQuestion] = useState("");
  const isActive = question.trim().length > 0;
  const sendIcon = useMemo(() => (isActive ? assets.sendActive : assets.sendDisabled), [isActive]);
  const lastMessage = messages[messages.length - 1];
  const showRefinedChoices = lastMessage?.kind === "refined_question";
  const showMentorRecommendations = lastMessage?.kind === "mentor_recommendations";
  const visibleMessages = showRefinedChoices ? messages.slice(-1) : showMentorRecommendations ? messages.slice(-2) : messages;
  const messageScrollRef = useRef<HTMLDivElement>(null);

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

  function handleSubmit() {
    if (!question.trim()) {
      return;
    }

    const userMessage: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      kind: "text",
      text: question.trim(),
    };

    setQuestion("");
    appendMessages([userMessage, ...mockAssistantReply(question)]);
  }

  function handleSendRefinedQuestion() {
    appendMessages([
      {
        id: `u-refined-send-${Date.now()}`,
        role: "user",
        kind: "text",
        compact: true,
        text: "이 질문으로 보내기",
      },
      {
        id: `a-mentors-${Date.now()}`,
        role: "assistant",
        kind: "mentor_recommendations",
      },
    ]);
  }

  function handleCancelRefinedQuestion() {
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
  }

  function handleMentorSelect(mentorName: string) {
    appendMessages([
      {
        id: `u-mentor-select-${Date.now()}`,
        role: "user",
        kind: "text",
        compact: true,
        text: `${mentorName}에게 보낼래`,
      },
      {
        id: `a-mentor-confirm-${Date.now()}`,
        role: "assistant",
        kind: "mentor_confirmation",
      },
    ]);
  }

  function handleConfirmMentorRequest() {
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
        text: "멘토에게 질문을 보내는 중이에요",
      },
      {
        id: `a-done-${Date.now()}`,
        role: "assistant",
        kind: "text",
        content: (
          <>
            멘토에게 질문을 보냈어요.
            <br />
            보통 24시간 이내에 답변을 받을 수 있어요. 기다리는 동안 이 질문을 더 보완하거나 다른 멘토에게도 요청할 수 있어요.
          </>
        ),
      },
    ]);
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

  function handleEditorComplete() {
    setMessages((current) => [
      ...current.filter((message) => message.kind !== "mentor_request_editor"),
      {
        id: `u-edit-complete-${Date.now()}`,
        role: "user",
        kind: "text",
        compact: true,
        text: "수정완료",
      },
      {
        id: `a-refined-again-${Date.now()}`,
        role: "assistant",
        kind: "refined_question",
      },
    ]);
  }

  return (
    <main className="flex h-dvh min-h-[720px] w-full bg-[#f9f9f9] py-2 pr-2 text-[#242424]">
      <ChatSidebar />

      <section className="relative flex min-w-0 flex-1 overflow-hidden rounded-2xl border border-[#eeeeee] bg-[#fefefe] shadow-[0_6px_20px_rgba(68,74,83,0.12)]">
        <div className="relative z-10 flex min-h-0 w-full flex-col items-center px-[clamp(24px,12.5vw,180px)]">
          <div className="flex min-h-0 w-full flex-1 flex-col items-center justify-end">
            <div className="flex min-h-0 w-full flex-1 flex-col gap-7 py-5">
              <ChatTitleBar onBack={() => setMessages(initialMessages)} />

              <div ref={messageScrollRef} className="min-h-0 flex-1 overflow-y-auto">
                <MessageList
                  messages={visibleMessages}
                  onMentorSelect={handleMentorSelect}
                  onConfirmMentorRequest={handleConfirmMentorRequest}
                  onEditRequest={handleEditRequest}
                  onEditorComplete={handleEditorComplete}
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
              />
            </div>
          </div>

          <div className="shrink-0 pb-6 pt-3">
            <ServiceBottomNavigation className="!mb-0 !mt-0" />
          </div>
        </div>
      </section>
    </main>
  );
}

function mockAssistantReply(input: string): ChatMessage[] {
  if (input.includes("조회수") || input.includes("작")) {
    return [
      {
        id: `a-refined-${Date.now()}`,
        role: "assistant",
        kind: "refined_question",
      },
    ];
  }

  return [
    {
      id: `a-${Date.now()}`,
      role: "assistant",
      kind: "text",
      content: (
        <>
          좋아요. 지금 질문은 더 구체화할 수 있어요.
          <br />
          어떤 직무, 어떤 경험, 어떤 판단을 받고 싶은지까지 적으면 멘토가 훨씬 정확하게 답할 수 있어요.
        </>
      ),
    },
  ];
}

function refinedQuestionText() {
  return "개인 인스타그램에서 자취 생활 팁 콘텐츠를 3개월간 운영했고, 릴스 12개와 카드뉴스 8개를 제작했습니다. 팔로워는 180명 정도지만 일부 릴스가 조회수 4,800회를 기록했습니다. 마케팅 포트폴리오에서 이 경험을 어떻게 구조화하고, 낮은 팔로워 수보다 콘텐츠 실험과 성과 분석을 설득력 있게 보여주려면 어떤 점을 강조해야 할까요?";
}

function ChatTitleBar({ onBack }: { onBack: () => void }) {
  return (
    <header className="flex h-8 w-full shrink-0 items-center gap-2">
      <button type="button" aria-label="뒤로가기" onClick={onBack} className="relative flex size-5 items-center justify-center">
        <Image src={assets.arrowLeft} alt="" width={8} height={15} draggable={false} />
      </button>
      <h1 className="min-w-0 flex-1 text-center text-[17px] font-semibold leading-[1.55]">비전공자 PM 준비</h1>
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
}: {
  messages: ChatMessage[];
  onMentorSelect: (mentorName: string) => void;
  onConfirmMentorRequest: () => void;
  onEditRequest: () => void;
  onEditorComplete: () => void;
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
}: {
  message: ChatMessage;
  onMentorSelect: (mentorName: string) => void;
  onConfirmMentorRequest: () => void;
  onEditRequest: () => void;
  onEditorComplete: () => void;
}) {
  if (message.role === "user") {
    return (
      <UserMessage actions={message.userActions} compact={message.compact}>
        {message.text}
      </UserMessage>
    );
  }

  if (message.kind === "refined_question") {
    return <RefinedQuestionMessage />;
  }

  if (message.kind === "mentor_recommendations") {
    return <MentorRecommendationsMessage onSelect={onMentorSelect} />;
  }

  if (message.kind === "mentor_confirmation") {
    return <MentorConfirmationMessage onConfirm={onConfirmMentorRequest} onEdit={onEditRequest} />;
  }

  if (message.kind === "mentor_request_status") {
    return <MentorRequestStatus onEditRequest={onEditRequest} text={message.text ?? ""} />;
  }

  if (message.kind === "mentor_request_editor") {
    return <MentorRequestEditor onComplete={onEditorComplete} />;
  }

  return (
    <AssistantBlock>
      {message.content ?? message.text}
      <MessageActions hidden />
    </AssistantBlock>
  );
}

function RefinedQuestionMessage() {
  return (
    <div className="w-full">
      <p className="text-[14px] font-normal leading-none text-[#9e9e9e]">멘토에게 보낼 질문</p>
      <section className="mt-1.5 w-full max-w-[600px] rounded-2xl border border-[#e0e0e0] bg-white px-6 py-5 shadow-[0_6px_10px_rgba(68,74,83,0.12)]">
        <div className="flex items-center gap-2 px-1">
          <Image src={assets.chat} alt="" width={20} height={20} draggable={false} />
          <h2 className="text-[16px] font-medium leading-[1.6] text-black">비전공자 PM 직무 준비</h2>
        </div>
        <div className="mt-2 rounded-3xl bg-[#f7f7f7] px-6 py-5 text-[16px] font-medium leading-[1.6] text-[#585858]">
          비전공자로 PM 직무를 준비하고 있습니다. 현재 학교 팀플에서 진행한 서비스 기획 프로젝트 하나를 포트폴리오에 넣으려고 하는데, 현업 PM 관점에서 이 경험이 충분히 설득력 있을지 궁금합니다. 특히 문제 정의, 사용자 리서치, 기능 우선순위, 화면 기획 중 어떤 부분을 강조해야 할지 조언 받고 싶습니다.
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

const mentors = [
  {
    name: "콘텐츠 마케터",
    experience: "3년 8개월",
    tags: ["콘텐츠 기획", "콘텐츠 마케팅", "브랜드 마케팅"],
    avatarColor: "#ffddb3",
    gradient: "radial-gradient(75% 34% at 50% 0%, rgba(255,221,179,0.5) 0%, rgba(255,255,255,0) 100%)",
  },
  {
    name: "브랜드 마케터",
    experience: "3년 8개월",
    tags: ["캠페인 기획", "브랜딩", "콘텐츠 마케팅"],
    avatarColor: "#efc4ad",
    gradient: "radial-gradient(75% 34% at 50% 0%, rgba(239,196,173,0.5) 0%, rgba(255,255,255,0) 100%)",
  },
  {
    name: "퍼포먼스 마케터",
    experience: "3년 8개월",
    tags: ["광고 기획", "콘텐츠 마케팅", "리포트 구성"],
    avatarColor: "#ecdfa5",
    gradient: "radial-gradient(75% 34% at 50% 0%, rgba(236,223,165,0.5) 0%, rgba(255,255,255,0) 100%)",
  },
];

function MentorRecommendationsMessage({ onSelect }: { onSelect: (mentorName: string) => void }) {
  return (
    <AssistantBlock>
      <div className="text-[15px] font-medium leading-[1.6] text-[#101010]">
        <p>
          작성한 질문에는 콘텐츠 운영 경험을 포트폴리오로 바꿔본 멘토가 잘 맞아요.
          <br />
          관심 직무와 막힌 지점을 기준으로 추천 멘토 3명을 찾았어요.
        </p>
        <div className="mt-5">
          <p>원하는 멘토를 직접 선택해 주세요.</p>
        </div>
      </div>
      <div className="mt-2 flex max-w-full flex-wrap gap-2">
        {mentors.map((mentor) => (
          <button
            key={mentor.name}
            type="button"
            onClick={() => onSelect(mentor.name)}
            className="flex h-[240px] w-[200px] flex-col gap-4 rounded-2xl border border-[#eeeeee] bg-white px-4 py-5 text-left shadow-[0_16px_12px_rgba(94,107,127,0.16)] transition hover:border-[#ffd60a] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ffa600]"
            style={{ backgroundImage: mentor.gradient }}
          >
            <span className="flex flex-col gap-2">
              <span className="flex size-10 items-center justify-center rounded-full" style={{ backgroundColor: mentor.avatarColor }}>
                <Image src={assets.avatar} alt="" width={14} height={16} draggable={false} />
              </span>
              <span className="flex flex-col">
                <span className="text-[15px] font-medium leading-[1.7] text-[#242424]">{mentor.name}</span>
                <span className="text-[14px] font-normal leading-none text-[#585858]">{mentor.experience}</span>
              </span>
            </span>
            <span className="flex h-[90px] flex-wrap content-start gap-x-1.5 gap-y-1">
              {mentor.tags.map((tag) => (
                <span key={tag} className="rounded-lg bg-[#eeeeee] px-2 py-1 text-[13px] font-medium leading-none text-[#585858]">
                  {tag}
                </span>
              ))}
            </span>
          </button>
        ))}
      </div>
      <MessageActions />
    </AssistantBlock>
  );
}

function MentorConfirmationMessage({ onConfirm, onEdit }: { onConfirm: () => void; onEdit: () => void }) {
  return (
    <AssistantBlock>
      <p>
        선택한 멘토에게 아래 질문을 보낼까요?
        <br />
        보내기 전에 내용을 한 번 더 수정할 수 있어요.
      </p>
      <div className="mt-4 max-w-[640px] rounded-3xl bg-[#f7f7f7] px-6 py-5 text-[15px] font-medium leading-[1.6] text-[#585858]">
        {refinedQuestionText()}
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

function MentorRequestEditor({ onComplete }: { onComplete: () => void }) {
  return (
    <div className="flex h-full w-full flex-col gap-2 pb-4">
      <p className="text-[14px] font-normal leading-none text-[#9e9e9e]">질문 직접 수정하기</p>
      <section className="w-full rounded-2xl border border-[#e0e0e0] bg-white px-6 py-5 shadow-[0_6px_10px_rgba(68,74,83,0.12)]">
        <div className="flex items-center gap-2 px-1">
          <Image src={assets.editLine} alt="" width={20} height={20} draggable={false} />
          <h2 className="text-[15px] font-medium leading-[1.6] text-black">비전공자 PM 직무 준비</h2>
        </div>
        <div className="mt-2 rounded-3xl bg-[#f7f7f7] px-6 py-5 text-[15px] font-medium leading-[1.6] text-[#585858]">
          비전공자로 PM 직무를 준비하고 있습니다. 현재 학교 팀플에서 진행한 서비스 기획 프로젝트 하나를 포트폴리오에 넣으려고 하는데, 현업 PM 관점에서 이 경험이 충분히 설득력 있을지 궁금합니다. 특히 문제 정의, 사용자 리서치, 기능 우선순위, 화면 기획 중 어떤 부분을 강조해야 할지 조언 받고 싶습니다.
        </div>
        <div className="mt-2 flex justify-end">
          <button
            type="button"
            onClick={onComplete}
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
  question,
  setQuestion,
  isActive,
  sendIcon,
  onSubmit,
}: {
  question: string;
  setQuestion: (value: string) => void;
  isActive: boolean;
  sendIcon: string;
  onSubmit: () => void;
}) {
  return (
    <form
      className="relative z-10 w-full rounded-2xl border border-[#eeeeee] bg-white px-6 pb-4 pt-6 shadow-[0_6px_10px_rgba(68,74,83,0.12)]"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <textarea
        value={question}
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
          disabled={!isActive}
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

function ChatSidebar() {
  return (
    <aside className="hidden h-full w-[296px] shrink-0 overflow-hidden rounded-lg bg-[#f9f9f9] p-6 lg:flex">
      <div className="flex min-h-0 w-full flex-col gap-7">
        <div className="flex min-h-0 flex-1 flex-col gap-7 overflow-hidden">
          <div className="flex shrink-0 flex-col items-end gap-3">
            <div className="flex items-end gap-5 p-2.5">
              <button type="button" aria-label="새 대화" className="relative size-5">
                <Image src={assets.writeNew} alt="" fill sizes="20px" draggable={false} />
              </button>
              <button type="button" aria-label="사이드바 접기" className="relative size-5">
                <Image src={assets.sidebarToggle} alt="" fill sizes="20px" draggable={false} />
              </button>
            </div>
            <div className="flex h-11 w-full items-center gap-1 rounded-xl bg-[#eeeeee] px-3 py-2">
              <span className="relative size-5 shrink-0">
                <Image src={assets.searchHandle} alt="" width={4} height={4} className="absolute bottom-0.5 right-0.5" draggable={false} />
                <Image src={assets.searchCircle} alt="" width={14} height={14} className="absolute left-0.5 top-0.5" draggable={false} />
              </span>
              <span className="text-[16px] font-medium leading-[1.6] text-[#9e9e9e]">검색</span>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
            <SidebarSection title="커피챗">
              <FolderItem label="답변 기다리는 질문" />
              <FolderItem label="답변 받은 질문" />
              {chatTopics.map((topic) => (
                <SidebarItem key={topic} label={topic} nested />
              ))}
            </SidebarSection>

            <SidebarSection title="최근 대화" className="mt-6">
              {recentChats.map((chat) => (
                <SidebarItem key={chat} label={chat} active={chat === "비전공자 PM 준비"} />
              ))}
            </SidebarSection>
          </div>
        </div>

        <div className="flex h-11 shrink-0 items-center rounded-xl px-3 py-2">
          <div className="flex items-center gap-3">
            <span className="relative flex size-8 items-center justify-center rounded-full bg-[#cecccb]">
              <Image src={assets.avatar} alt="" width={14} height={16} draggable={false} />
            </span>
            <div className="flex items-center gap-2">
              <span className="text-[15px] font-medium leading-[1.7]">이름</span>
              <span className="rounded-lg bg-[#ffddb3] px-2 py-1 text-[14px] font-medium leading-none text-[#ce5f1a]">멘티</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}

function SidebarSection({
  title,
  children,
  className,
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("flex w-full flex-col gap-3", className)}>
      <h2 className="px-1 text-[14px] font-medium leading-none text-[#969696]">{title}</h2>
      <div className="flex w-full flex-col gap-1">{children}</div>
    </section>
  );
}

function FolderItem({ label }: { label: string }) {
  return (
    <button type="button" className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left">
      <Image src={assets.folder} alt="" width={20} height={20} draggable={false} />
      <span className="min-w-0 flex-1 truncate text-[16px] font-medium leading-[1.6]">{label}</span>
    </button>
  );
}

function SidebarItem({ label, active = false, nested = false }: { label: string; active?: boolean; nested?: boolean }) {
  return (
    <button
      type="button"
      className={cn(
        "flex w-full items-center rounded-xl py-2 text-left",
        nested ? "pl-10 pr-3" : "px-3",
        active && "bg-[#eeeeee]",
      )}
    >
      <span className="min-w-0 flex-1 truncate text-[16px] font-medium leading-[1.6]">{label}</span>
    </button>
  );
}
