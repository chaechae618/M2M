"use client";

import { Download, FileText, Pencil, Upload, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { apiAssetUrl, apiRequest, jsonRequest } from "@/shared/api/client";
import { routes } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/cn";

type MenteeProfile = {
  id: string;
  email: string;
  name: string;
  currentStatus: string;
  background: Record<string, unknown>;
  consideringOptions: string[];
  targetRoles: string[];
  interestDomains: string[];
  resumeUrl: string | null;
  resumeFileName: string | null;
  portfolioUrl: string | null;
  portfolioFileName: string | null;
  updatedAt: string;
};

type FileUpload = { fileType: string; fileName: string; url: string; size: number };

const statusOptions = [
  ["student", "학생"],
  ["job_seeker", "취업준비"],
  ["career_change", "이직/전환"],
  ["employed", "재직중"],
  ["other", "기타"],
] as const;

function statusLabel(status: string) {
  return statusOptions.find(([value]) => value === status)?.[1] ?? status;
}

export default function MyPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<MenteeProfile | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState("");
  const [status, setStatus] = useState("student");
  const [interestsText, setInterestsText] = useState("");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    apiRequest<MenteeProfile>("mentees/me")
      .then((data) => {
        setProfile(data);
        setName(data.name);
        setStatus(data.currentStatus);
        setInterestsText(data.interestDomains.join(", "));
      })
      .catch((requestError) => {
        if (requestError && typeof requestError === "object" && "status" in requestError && requestError.status === 401) {
          router.replace(routes.login);
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "프로필을 불러오지 못했습니다.");
      });
  }, [router]);

  async function saveProfile() {
    if (!isEditing) {
      setIsEditing(true);
      return;
    }
    setError("");
    setIsSaving(true);
    try {
      const updated = await apiRequest<MenteeProfile>(
        "mentees/me",
        jsonRequest("PATCH", {
          name,
          currentStatus: status,
          interestDomains: interestsText.split(",").map((item) => item.trim()).filter(Boolean),
        }),
      );
      setProfile(updated);
      setIsEditing(false);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "프로필을 저장하지 못했습니다.");
    } finally {
      setIsSaving(false);
    }
  }

  function applyUploadedFile(kind: "resume" | "portfolio", upload: FileUpload) {
    setProfile((current) => current ? {
      ...current,
      resumeUrl: kind === "resume" ? upload.url : current.resumeUrl,
      resumeFileName: kind === "resume" ? upload.fileName : current.resumeFileName,
      portfolioUrl: kind === "portfolio" ? upload.url : current.portfolioUrl,
      portfolioFileName: kind === "portfolio" ? upload.fileName : current.portfolioFileName,
    } : current);
  }

  const interests = profile?.interestDomains.length ? profile.interestDomains : profile?.targetRoles ?? [];

  return (
    <main className="min-h-dvh bg-white px-5 pb-36 pt-14 sm:px-10 sm:pt-16 lg:px-12">
      <div className="mx-auto w-full max-w-[744px]">
        <h1 className="text-[23px] font-bold leading-[1.6] text-[#242424]">프로필</h1>
        {!profile && !error ? <p className="mt-12 text-[16px] text-[#7a7a7a]">프로필을 불러오는 중...</p> : null}
        {error ? <p role="alert" className="mt-6 text-[14px] text-red-600">{error}</p> : null}

        {profile ? (
          <section className="mt-[60px]">
            <div className="flex items-center gap-6">
              <div className="relative flex size-[72px] shrink-0 items-center justify-center rounded-full bg-[#d7d4d4] text-[#585858]">
                <UserRound size={32} strokeWidth={1.5} />
                <button
                  type="button"
                  aria-label="프로필 이미지 수정 준비 중"
                  title="프로필 이미지 수정은 준비 중입니다."
                  disabled
                  className="absolute -bottom-1 -right-1 flex size-7 cursor-not-allowed items-center justify-center rounded-full border border-white bg-[#eeeeee] text-[#9e9e9e] shadow-[0_1px_4px_rgba(0,0,0,0.12)]"
                >
                  <Pencil size={12} strokeWidth={1.7} />
                </button>
              </div>
              {isEditing ? (
                <input
                  aria-label="이름"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  className="h-10 w-48 rounded-lg border border-[#d8d8d8] px-3 text-[20px] font-semibold text-[#242424] outline-none focus:border-[#ffad00]"
                />
              ) : (
                <div>
                  <p className="text-[20px] font-semibold leading-[1.55] text-[#242424]">{profile.name}</p>
                  <p className="mt-1 text-[14px] text-[#9e9e9e]">{profile.email}</p>
                </div>
              )}
            </div>

            <div className="my-10 h-px w-full bg-[#eeeeee]" />

            <div className="flex flex-col gap-7">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-[19px] font-bold leading-none text-[#242424]">멘티 프로필 정보</h2>
                  <p className="mt-2 text-[16px] leading-normal text-[#585858]">관심 분야에 맞는 멘토를 연결하고 질문 이해에 필요한 정보예요.</p>
                </div>
                <button
                  type="button"
                  onClick={saveProfile}
                  disabled={isSaving}
                  className="h-9 shrink-0 rounded-lg bg-[#ffd60a] px-3 text-[13px] font-bold text-[#51431f] disabled:opacity-60"
                >
                  {isSaving ? "저장 중..." : isEditing ? "완료" : "수정하기"}
                </button>
              </div>

              <div className="flex flex-col gap-7 pt-1">
                <ProfileRow label="현재 상태">
                  {isEditing ? (
                    <select value={status} onChange={(event) => setStatus(event.target.value)} className="h-9 w-48 rounded-lg border border-[#d8d8d8] bg-white px-3 text-[16px] text-[#242424] outline-none focus:border-[#ffad00]">
                      {statusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                    </select>
                  ) : <span>{statusLabel(profile.currentStatus)}</span>}
                </ProfileRow>

                <ProfileRow label="관심 분야">
                  {isEditing ? (
                    <input value={interestsText} onChange={(event) => setInterestsText(event.target.value)} placeholder="쉼표로 구분해주세요." className="h-9 w-full rounded-lg border border-[#d8d8d8] px-3 text-[16px] text-[#242424] outline-none focus:border-[#ffad00]" />
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {interests.length ? interests.map((interest) => <span key={interest} className="rounded-lg bg-[#eeeeee] px-2 py-1 text-[15px] leading-none text-[#585858]">{interest}</span>) : <span className="text-[#9e9e9e]">등록된 관심 분야가 없어요.</span>}
                    </div>
                  )}
                </ProfileRow>

                <ProfileRow label="이력서" align="start">
                  <div className="w-full">
                    <FileEntry kind="resume" name="이력서" url={profile.resumeUrl} fileName={profile.resumeFileName} accept=".pdf,.docx" onUploaded={applyUploadedFile} onError={setError} />
                    <p className="mt-1 pl-8 text-[14px] leading-[1.4] text-[#9e9e9e]">이력서는 다른 사람들에게 공개되지 않아요.</p>
                  </div>
                </ProfileRow>

                <ProfileRow label="포트폴리오" align="start">
                  <FileEntry kind="portfolio" name="포트폴리오" url={profile.portfolioUrl} fileName={profile.portfolioFileName} accept=".pdf,.pptx" onUploaded={applyUploadedFile} onError={setError} />
                </ProfileRow>
              </div>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}

function ProfileRow({ label, children, align = "center" }: { label: string; children: ReactNode; align?: "center" | "start" }) {
  return (
    <div className={cn("flex flex-col gap-2 sm:flex-row sm:gap-4", align === "start" ? "sm:items-start" : "sm:items-center")}>
      <p className="w-[111px] shrink-0 text-[18px] font-medium leading-[1.6] text-[#9e9e9e]">{label}</p>
      <div className="min-w-0 flex-1 text-[18px] font-medium leading-[1.6] text-[#242424]">{children}</div>
    </div>
  );
}

function FileEntry({
  kind,
  name,
  url,
  fileName,
  accept,
  onUploaded,
  onError,
}: {
  kind: "resume" | "portfolio";
  name: string;
  url: string | null;
  fileName: string | null;
  accept: string;
  onUploaded: (kind: "resume" | "portfolio", upload: FileUpload) => void;
  onError: (message: string) => void;
}) {
  const [isUploading, setIsUploading] = useState(false);
  const downloadUrl = apiAssetUrl(url);

  async function upload(file: File | null) {
    if (!file) return;
    setIsUploading(true);
    onError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const result = await apiRequest<FileUpload>(`mentees/me/${kind}`, { method: "POST", body: formData });
      onUploaded(kind, result);
    } catch (requestError) {
      onError(requestError instanceof Error ? requestError.message : "파일을 업로드하지 못했습니다.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <FileText size={20} className="shrink-0 text-[#585858]" />
      <span className="min-w-0 flex-1 truncate text-[18px] font-medium leading-[1.6] text-[#242424]">{fileName || (url ? `${name} 등록됨` : `${name} 없음`)}</span>
      <label className="flex size-7 shrink-0 cursor-pointer items-center justify-center rounded-lg bg-[#eeeeee] text-[#585858]" title={`${name} 업로드`}>
        <Upload size={18} strokeWidth={1.6} />
        <input type="file" accept={accept} disabled={isUploading} className="sr-only" onChange={(event) => upload(event.target.files?.[0] ?? null)} />
      </label>
      {downloadUrl ? (
        <a href={downloadUrl} target="_blank" rel="noreferrer" aria-label={`${name} 다운로드`} className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-[#eeeeee] text-[#585858]">
          <Download size={18} strokeWidth={1.6} />
        </a>
      ) : null}
    </div>
  );
}
