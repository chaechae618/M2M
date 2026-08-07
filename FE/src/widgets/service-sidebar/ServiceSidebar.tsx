"use client";

import Image from "next/image";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { CONSULTATIONS_CHANGED_EVENT } from "@/features/consultation/model/events";
import { apiRequest } from "@/shared/api/client";
import type { AuthUser } from "@/shared/api/types";
import { cn } from "@/shared/lib/cn";

type ConsultationSummary = {
  id: string;
  title: string;
  status: string;
};

const answeredStatuses = new Set([
  "ai_answered",
  "persona_answered",
  "awaiting_feedback",
  "assetizing",
  "assetized",
  "completed",
]);

const hiddenStatuses = new Set(["cancelled"]);

const assets = {
  avatar: "/figma-assets/chat/avatar-person.svg",
  folder: "/figma-assets/chat/folder.svg",
  searchCircle: "/figma-assets/chat/search-circle.svg",
  searchHandle: "/figma-assets/chat/search-handle.svg",
  sidebarToggle: "/figma-assets/chat/sidebar-toggle.svg",
  writeNew: "/figma-assets/chat/write-new.svg",
};

type ServiceSidebarContextValue = {
  isCollapsed: boolean;
  toggleSidebar: () => void;
  expandSidebar: () => void;
};

const ServiceSidebarContext = createContext<ServiceSidebarContextValue | null>(null);

export function ServiceSidebarProvider({ children }: { children: ReactNode }) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  function toggleSidebar() {
    setIsCollapsed((current) => !current);
  }

  function expandSidebar() {
    setIsCollapsed(false);
  }

  return <ServiceSidebarContext.Provider value={{ isCollapsed, toggleSidebar, expandSidebar }}>{children}</ServiceSidebarContext.Provider>;
}

export function ServiceSidebar() {
  const context = useContext(ServiceSidebarContext);
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeSessionId = searchParams.get("session");
  const [userName, setUserName] = useState("이름");
  const [recentChats, setRecentChats] = useState<ConsultationSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    apiRequest<AuthUser>("auth/me")
      .then((user) => setUserName(user.name))
      .catch(() => {});
  }, []);

  const loadConsultations = useCallback(() => {
    apiRequest<{ items: ConsultationSummary[] }>("consultations?limit=100")
      .then((result) => setRecentChats(result.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadConsultations();
    window.addEventListener(CONSULTATIONS_CHANGED_EVENT, loadConsultations);
    return () => window.removeEventListener(CONSULTATIONS_CHANGED_EVENT, loadConsultations);
  }, [loadConsultations]);

  if (!context) {
    throw new Error("ServiceSidebar must be used inside ServiceSidebarProvider.");
  }

  const { isCollapsed, toggleSidebar, expandSidebar } = context;
  const startNewChat = () => router.push(`/chat?new=${Date.now()}`);

  return (
    <aside
      className={cn(
        "hidden h-full shrink-0 overflow-hidden rounded-lg bg-[#f9f9f9] p-6 transition-[width] duration-200 ease-out lg:flex",
        isCollapsed ? "w-[68px]" : "w-[296px]",
      )}
    >
      {isCollapsed ? (
        <div className="flex h-full w-full flex-col items-center justify-between">
          <div className="flex flex-col items-center gap-5">
            <SidebarIconButton label="사이드바 펼치기" icon={assets.sidebarToggle} onClick={toggleSidebar} />
            <SidebarIconButton label="대화 검색" icon={assets.searchCircle} onClick={expandSidebar} />
            <SidebarIconButton label="새 대화" icon={assets.writeNew} onClick={startNewChat} />
          </div>
          <UserAvatar collapsed />
        </div>
      ) : (
        <ExpandedSidebar
          userName={userName}
          recentChats={recentChats}
          activeSessionId={activeSessionId}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onToggle={toggleSidebar}
          onNewChat={startNewChat}
          onSelectChat={(id) => router.push(`/chat?session=${id}`)}
        />
      )}
    </aside>
  );
}

function ExpandedSidebar({
  userName,
  recentChats,
  activeSessionId,
  searchQuery,
  onSearchChange,
  onToggle,
  onNewChat,
  onSelectChat,
}: {
  userName: string;
  recentChats: ConsultationSummary[];
  activeSessionId: string | null;
  searchQuery: string;
  onSearchChange: (value: string) => void;
  onToggle: () => void;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
}) {
  const [expandedFolder, setExpandedFolder] = useState<"waiting" | "answered" | null>(null);
  const visibleChats = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLocaleLowerCase("ko");
    return recentChats.filter((chat) => {
      if (hiddenStatuses.has(chat.status)) return false;
      return !normalizedQuery || chat.title.toLocaleLowerCase("ko").includes(normalizedQuery);
    });
  }, [recentChats, searchQuery]);
  const waitingChats = visibleChats.filter((chat) => !answeredStatuses.has(chat.status));
  const answeredChats = visibleChats.filter((chat) => answeredStatuses.has(chat.status));

  return (
    <div className="flex min-h-0 w-full flex-col gap-7">
      <div className="flex min-h-0 flex-1 flex-col gap-7 overflow-hidden">
        <div className="flex shrink-0 flex-col items-end gap-3">
          <div className="flex items-end gap-5 p-2.5">
            <SidebarIconButton label="새 대화" icon={assets.writeNew} onClick={onNewChat} />
            <SidebarIconButton label="사이드바 접기" icon={assets.sidebarToggle} onClick={onToggle} />
          </div>
          <label className="flex h-11 w-full items-center gap-1 rounded-xl bg-[#eeeeee] px-3 py-2">
            <span className="relative size-5 shrink-0">
              <Image src={assets.searchHandle} alt="" width={4} height={4} className="absolute bottom-0.5 right-0.5" draggable={false} />
              <Image src={assets.searchCircle} alt="" width={14} height={14} className="absolute left-0.5 top-0.5" draggable={false} />
            </span>
            <span className="sr-only">대화 검색</span>
            <input
              type="search"
              value={searchQuery}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="검색"
              className="min-w-0 flex-1 bg-transparent text-[15px] font-medium leading-[1.6] text-[#242424] outline-none placeholder:text-[#9e9e9e]"
            />
          </label>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
          <SidebarSection title="커피챗">
            <FolderItem
              label="답변 기다리는 질문"
              count={waitingChats.length}
              expanded={expandedFolder === "waiting"}
              onClick={() => setExpandedFolder((current) => current === "waiting" ? null : "waiting")}
            />
            {expandedFolder === "waiting" ? (
              <FolderChats chats={waitingChats} activeSessionId={activeSessionId} onSelectChat={onSelectChat} />
            ) : null}
            <FolderItem
              label="답변 받은 질문"
              count={answeredChats.length}
              expanded={expandedFolder === "answered"}
              onClick={() => setExpandedFolder((current) => current === "answered" ? null : "answered")}
            />
            {expandedFolder === "answered" ? (
              <FolderChats chats={answeredChats} activeSessionId={activeSessionId} onSelectChat={onSelectChat} />
            ) : null}
          </SidebarSection>

          <SidebarSection title="최근 대화" className="mt-6">
            {visibleChats.slice(0, 10).map((chat) => (
              <SidebarItem key={chat.id} label={chat.title} active={chat.id === activeSessionId} onClick={() => onSelectChat(chat.id)} />
            ))}
            {visibleChats.length === 0 ? <SidebarEmpty label={searchQuery ? "검색 결과가 없어요" : "아직 대화가 없어요"} /> : null}
          </SidebarSection>
        </div>
      </div>

      <div className="flex h-11 shrink-0 items-center rounded-xl px-3 py-2">
        <div className="flex items-center gap-3">
          <UserAvatar />
          <div className="flex items-center gap-2">
            <span className="text-[15px] font-medium leading-[1.7] text-[#242424]">{userName}</span>
            <span className="rounded-lg bg-[#ffddb3] px-2 py-1 text-[14px] font-medium leading-none text-[#ce5f1a]">멘티</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SidebarIconButton({ label, icon, onClick }: { label: string; icon: string; onClick?: () => void }) {
  return (
    <button type="button" aria-label={label} onClick={onClick} className="relative flex size-5 shrink-0 items-center justify-center">
      <Image src={icon} alt="" fill sizes="20px" draggable={false} />
    </button>
  );
}

function UserAvatar({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <span className={cn("relative flex size-8 items-center justify-center rounded-full", collapsed ? "bg-[#d7d4d4]" : "bg-[#cecccb]")}>
      <Image src={assets.avatar} alt="" width={14} height={16} draggable={false} />
    </span>
  );
}

function SidebarSection({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className={cn("flex w-full flex-col gap-3", className)}>
      <h2 className="px-1 text-[14px] font-medium leading-none text-[#969696]">{title}</h2>
      <div className="flex w-full flex-col gap-1">{children}</div>
    </section>
  );
}

function FolderItem({ label, count, expanded, onClick }: { label: string; count: number; expanded: boolean; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} aria-expanded={expanded} className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left hover:bg-[#eeeeee]">
      <Image src={assets.folder} alt="" width={20} height={20} draggable={false} />
      <span className="min-w-0 flex-1 truncate text-[16px] font-medium leading-[1.6] text-[#242424]">{label}</span>
      <span className="text-[13px] font-medium text-[#9e9e9e]">{count}</span>
      {expanded ? <ChevronDown aria-hidden className="size-4 text-[#9e9e9e]" /> : <ChevronRight aria-hidden className="size-4 text-[#9e9e9e]" />}
    </button>
  );
}

function FolderChats({ chats, activeSessionId, onSelectChat }: { chats: ConsultationSummary[]; activeSessionId: string | null; onSelectChat: (id: string) => void }) {
  if (chats.length === 0) return <SidebarEmpty label="해당 질문이 없어요" />;
  return chats.map((chat) => (
    <SidebarItem key={chat.id} label={chat.title} nested active={chat.id === activeSessionId} onClick={() => onSelectChat(chat.id)} />
  ));
}

function SidebarEmpty({ label }: { label: string }) {
  return <p className="px-3 py-2 text-[13px] font-medium text-[#9e9e9e]">{label}</p>;
}

function SidebarItem({
  label,
  active = false,
  nested = false,
  onClick,
}: {
  label: string;
  active?: boolean;
  nested?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn("flex w-full items-center rounded-xl py-2 text-left", nested ? "pl-10 pr-3" : "px-3", active && "bg-[#eeeeee]")}
    >
      <span className="min-w-0 flex-1 truncate text-[16px] font-medium leading-[1.6] text-[#242424]">{label}</span>
    </button>
  );
}
