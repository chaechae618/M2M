"use client";

import { Download, FileText, Link as LinkIcon, Pencil, UserRound } from "lucide-react";
import { useState, type ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

const interests = ["콘텐츠 마케팅", "콘텐츠 기획", "브랜드 마케팅"];

export default function MyPage() {
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState("김이름");
  const [status, setStatus] = useState("학생");

  return (
    <main className="min-h-dvh bg-white px-5 pb-36 pt-14 sm:px-10 sm:pt-16 lg:px-12">
      <div className="mx-auto w-full max-w-[744px]">
        <h1 className="text-[23px] font-bold leading-[1.6] text-[#242424]">프로필</h1>

        <section className="mt-[60px]">
          <div className="flex items-center gap-6">
            <div className="relative flex size-[72px] shrink-0 items-center justify-center rounded-full bg-[#d7d4d4] text-[#585858]">
              <UserRound size={32} strokeWidth={1.5} />
              <button
                type="button"
                aria-label="프로필 이미지 수정"
                className="absolute -bottom-1 -right-1 flex size-7 items-center justify-center rounded-full border border-white bg-[#eeeeee] text-[#585858] shadow-[0_1px_4px_rgba(0,0,0,0.12)]"
              >
                <Pencil size={12} strokeWidth={1.7} />
              </button>
            </div>
            {isEditing ? (
              <label className="sr-only" htmlFor="profile-name">
                이름
              </label>
            ) : null}
            {isEditing ? (
              <input
                id="profile-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="h-10 w-48 rounded-lg border border-[#d8d8d8] px-3 text-[20px] font-semibold text-[#242424] outline-none focus:border-[#ffad00]"
              />
            ) : (
              <p className="text-[20px] font-semibold leading-[1.55] text-[#242424]">{name}</p>
            )}
          </div>

          <div className="my-10 h-px w-full bg-[#eeeeee]" />

          <div className="flex flex-col gap-7">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="text-[19px] font-bold leading-none text-[#242424]">멘티 프로필 정보</h2>
                <p className="mt-2 text-[16px] leading-normal text-[#585858]">
                  관심 분야에 맞는 멘토를 연결하고 질문 이해에 필요한 정보예요.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsEditing((value) => !value)}
                className="h-9 shrink-0 rounded-lg bg-[#ffd60a] px-3 text-[13px] font-bold text-[#51431f]"
              >
                {isEditing ? "완료" : "수정하기"}
              </button>
            </div>

            <div className="flex flex-col gap-7 pt-1">
              <ProfileRow label="현재 상태">
                {isEditing ? (
                  <input
                    value={status}
                    onChange={(event) => setStatus(event.target.value)}
                    className="h-9 w-48 rounded-lg border border-[#d8d8d8] px-3 text-[18px] text-[#242424] outline-none focus:border-[#ffad00]"
                  />
                ) : (
                  <span>{status}</span>
                )}
              </ProfileRow>

              <ProfileRow label="관심 분야">
                <div className="flex flex-wrap gap-2">
                  {interests.map((interest) => (
                    <span key={interest} className="rounded-lg bg-[#eeeeee] px-2 py-1 text-[15px] leading-none text-[#585858]">
                      {interest}
                    </span>
                  ))}
                </div>
              </ProfileRow>

              <ProfileRow label="이력서" align="start">
                <div className="w-full">
                  <FileEntry icon={<FileText size={20} />} name="2026_상반기_cv.pdf" />
                  <p className="mt-1 pl-8 text-[14px] leading-[1.4] text-[#9e9e9e]">이력서는 다른 사람들에게 공개되지 않아요.</p>
                </div>
              </ProfileRow>

              <ProfileRow label="포트폴리오" align="start">
                <div className="flex w-full flex-col gap-3">
                  <div className="flex items-center gap-3 text-[18px] leading-[1.6] text-[#242424]">
                    <LinkIcon size={20} className="shrink-0 text-[#585858]" />
                    <a href="https://0000.com" className="truncate hover:underline">0000.com</a>
                  </div>
                  <FileEntry icon={<FileText size={20} />} name="2026_상반기_포트폴리오.pdf" />
                </div>
              </ProfileRow>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function ProfileRow({
  label,
  children,
  align = "center",
}: {
  label: string;
  children: ReactNode;
  align?: "center" | "start";
}) {
  return (
    <div className={cn("flex flex-col gap-2 sm:flex-row sm:gap-4", align === "start" ? "sm:items-start" : "sm:items-center")}>
      <p className="w-[111px] shrink-0 text-[18px] font-medium leading-[1.6] text-[#9e9e9e]">{label}</p>
      <div className="min-w-0 flex-1 text-[18px] font-medium leading-[1.6] text-[#242424]">{children}</div>
    </div>
  );
}

function FileEntry({ icon, name }: { icon: ReactNode; name: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="shrink-0 text-[#585858]">{icon}</span>
      <span className="min-w-0 flex-1 truncate text-[18px] font-medium leading-[1.6] text-[#242424]">{name}</span>
      <button
        type="button"
        aria-label={`${name} 다운로드`}
        className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-[#eeeeee] text-[#585858]"
      >
        <Download size={20} strokeWidth={1.6} />
      </button>
    </div>
  );
}
