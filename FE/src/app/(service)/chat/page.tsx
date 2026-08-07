"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ChatScreen } from "@/features/consultation/components/ChatScreen";
import { useConsultationChat } from "@/features/consultation/hooks/useConsultationChat";

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
  const resumeSessionId = searchParams.get("session");

  return (
    <ChatSession
      key={resumeSessionId ?? newChatToken ?? "current-chat"}
      startsAsNewChat={!resumeSessionId}
      resumeSessionId={resumeSessionId}
    />
  );
}

function ChatSession({
  startsAsNewChat,
  resumeSessionId,
}: {
  startsAsNewChat: boolean;
  resumeSessionId: string | null;
}) {
  const chat = useConsultationChat({ startsAsNewChat, resumeSessionId });

  return <ChatScreen {...chat} />;
}
