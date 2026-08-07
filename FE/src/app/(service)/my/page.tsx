"use client";

import { Download, FileText, LoaderCircle, Pencil, Trash2, Upload, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { apiRequest, jsonRequest } from "@/shared/api/client";
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

type FileUpload = { fileType: string; fileName: string; url: string; size: number; contentType: string };

const statusOptions = [
  ["student", "학생"],
  ["job_seeker", "취업준비"],
  ["career_change", "이직/전환"],
  ["employed", "재직중"],
  ["career_exploration", "진로탐색"],
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

  function setDraftFromProfile(data: MenteeProfile) {
    setName(data.name);
    setStatus(data.currentStatus);
    setInterestsText(data.interestDomains.join(", "));
  }

  useEffect(() => {
    apiRequest<MenteeProfile>("mentees/me")
      .then((data) => {
        setProfile(data);
        setDraftFromProfile(data);
      })
      .catch((requestError) => {
        if (requestError && typeof requestError === "object" && "status" in requestError && requestError.status === 401) {
          router.replace(routes.login);
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "프로필을 불러오지 못했습니다.");
      });
  }, [router]);

  function beginEditing() {
    if (!profile) return;
    setDraftFromProfile(profile);
    setError("");
    setIsEditing(true);
  }

  function cancelEditing() {
    if (!profile || isSaving) return;
    setDraftFromProfile(profile);
    setError("");
    setIsEditing(false);
  }

  async function saveProfile() {
    if (!profile || isSaving) return;
    setError("");
    const normalizedName = name.trim();
    const interestDomains = Array.from(
      new Set(interestsText.split(",").map((item) => item.trim()).filter(Boolean)),
    );
    if (normalizedName.length < 2) {
      setError("이름은 두 글자 이상 입력해주세요.");
      return;
    }
    if (interestDomains.length > 10 || interestDomains.some((item) => item.length > 50)) {
      setError("관심 분야는 50자 이내로 최대 10개까지 등록할 수 있어요.");
      return;
    }
    setIsSaving(true);
    try {
      const updated = await apiRequest<MenteeProfile>(
        "mentees/me",
        jsonRequest("PATCH", {
          name: normalizedName,
          currentStatus: status,
          interestDomains,
        }),
      );
      setProfile(updated);
      setDraftFromProfile(updated);
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

  function applyDeletedFile(kind: "resume" | "portfolio") {
    setProfile((current) => current ? {
      ...current,
      resumeUrl: kind === "resume" ? null : current.resumeUrl,
      resumeFileName: kind === "resume" ? null : current.resumeFileName,
      portfolioUrl: kind === "portfolio" ? null : current.portfolioUrl,
      portfolioFileName: kind === "portfolio" ? null : current.portfolioFileName,
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
                {isEditing ? (
                  <div className="flex shrink-0 items-center gap-2">
                    <button type="button" onClick={cancelEditing} disabled={isSaving} className="h-9 rounded-lg bg-[#eeeeee] px-3 text-[13px] font-bold text-[#585858] disabled:opacity-60">취소</button>
                    <button type="button" onClick={saveProfile} disabled={isSaving} className="flex h-9 min-w-[60px] items-center justify-center gap-1.5 rounded-lg bg-[#ffd60a] px-3 text-[13px] font-bold text-[#51431f] disabled:opacity-60">
                      {isSaving ? <><LoaderCircle aria-hidden className="size-4 animate-spin" /> 저장 중</> : "저장"}
                    </button>
                  </div>
                ) : (
                  <button type="button" onClick={beginEditing} className="h-9 shrink-0 rounded-lg bg-[#ffd60a] px-3 text-[13px] font-bold text-[#51431f]">수정하기</button>
                )}
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
                    <FileEntry kind="resume" name="이력서" url={profile.resumeUrl} fileName={profile.resumeFileName} accept=".pdf" maxSizeMb={10} isEditing={isEditing} onUploaded={applyUploadedFile} onDeleted={applyDeletedFile} />
                    <p className="mt-1 pl-8 text-[14px] leading-[1.4] text-[#9e9e9e]">이력서는 다른 사람들에게 공개되지 않아요.</p>
                  </div>
                </ProfileRow>

                <ProfileRow label="포트폴리오" align="start">
                  <FileEntry kind="portfolio" name="포트폴리오" url={profile.portfolioUrl} fileName={profile.portfolioFileName} accept=".pdf,.pptx" maxSizeMb={20} isEditing={isEditing} onUploaded={applyUploadedFile} onDeleted={applyDeletedFile} />
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
  maxSizeMb,
  isEditing,
  onUploaded,
  onDeleted,
}: {
  kind: "resume" | "portfolio";
  name: string;
  url: string | null;
  fileName: string | null;
  accept: string;
  maxSizeMb: number;
  isEditing: boolean;
  onUploaded: (kind: "resume" | "portfolio", upload: FileUpload) => void;
  onDeleted: (kind: "resume" | "portfolio") => void;
}) {
  const [isUploading, setIsUploading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [fileError, setFileError] = useState("");
  const allowedExtensions = accept.split(",");
  const downloadUrl = url ? `/api/backend/mentees/me/${kind}/file` : null;

  async function upload(file: File | null) {
    if (!file) return;
    const extension = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
    if (!allowedExtensions.includes(extension)) {
      setFileError(`${name}는 ${allowedExtensions.join(", ").toUpperCase()} 파일만 등록할 수 있어요.`);
      return;
    }
    if (file.size > maxSizeMb * 1024 * 1024) {
      setFileError(`${name} 파일은 ${maxSizeMb}MB 이하만 등록할 수 있어요.`);
      return;
    }
    setIsUploading(true);
    setFileError("");
    setStatusMessage("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const result = await apiRequest<FileUpload>(`mentees/me/${kind}`, { method: "POST", body: formData });
      onUploaded(kind, result);
      setStatusMessage(`${result.fileName} 업로드를 완료했어요.`);
    } catch (requestError) {
      setFileError(requestError instanceof Error ? requestError.message : "파일을 업로드하지 못했습니다.");
    } finally {
      setIsUploading(false);
    }
  }

  async function deleteFile() {
    if (!url || isDeleting || !window.confirm(`등록된 ${name} 파일을 삭제할까요?`)) return;
    setIsDeleting(true);
    setFileError("");
    setStatusMessage("");
    try {
      await apiRequest(`mentees/me/${kind}`, { method: "DELETE" });
      onDeleted(kind);
      setStatusMessage(`${name} 파일을 삭제했어요.`);
    } catch (requestError) {
      setFileError(requestError instanceof Error ? requestError.message : "파일을 삭제하지 못했습니다.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div className="w-full">
      <div className="flex items-center gap-3">
        <FileText size={20} className="shrink-0 text-[#585858]" />
        <span className="min-w-0 flex-1 truncate text-[18px] font-medium leading-[1.6] text-[#242424]">{fileName || (url ? `${name} 등록됨` : `${name} 없음`)}</span>
        {isEditing ? (
          <label className={cn("flex size-8 shrink-0 items-center justify-center rounded-lg bg-[#eeeeee] text-[#585858]", isUploading || isDeleting ? "cursor-not-allowed opacity-50" : "cursor-pointer")} title={`${name} 업로드`}>
            {isUploading ? <LoaderCircle aria-hidden className="size-[18px] animate-spin" /> : <Upload aria-hidden size={18} strokeWidth={1.6} />}
            <span className="sr-only">{name} 업로드</span>
            <input
              type="file"
              accept={accept}
              disabled={isUploading || isDeleting}
              className="sr-only"
              onChange={(event) => {
                void upload(event.target.files?.[0] ?? null);
                event.currentTarget.value = "";
              }}
            />
          </label>
        ) : null}
        {downloadUrl ? (
          <a href={downloadUrl} aria-label={`${name} 다운로드`} className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-[#eeeeee] text-[#585858]">
            <Download size={18} strokeWidth={1.6} />
          </a>
        ) : null}
        {isEditing && url ? (
          <button type="button" onClick={deleteFile} disabled={isUploading || isDeleting} aria-label={`${name} 삭제`} className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-[#eeeeee] text-[#585858] disabled:opacity-50">
            {isDeleting ? <LoaderCircle aria-hidden className="size-[18px] animate-spin" /> : <Trash2 aria-hidden size={18} strokeWidth={1.6} />}
          </button>
        ) : null}
      </div>
      {isEditing ? <p className="mt-1 pl-8 text-[13px] leading-[1.4] text-[#9e9e9e]">{allowedExtensions.join(", ").toUpperCase()} · 최대 {maxSizeMb}MB</p> : null}
      <div aria-live="polite" className="pl-8">
        {fileError ? <p role="alert" className="mt-1 text-[13px] text-red-600">{fileError}</p> : null}
        {statusMessage ? <p className="mt-1 text-[13px] text-[#7a6500]">{statusMessage}</p> : null}
      </div>
    </div>
  );
}
