"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";
import { Button } from "@/shared/components/Button";
import { Checkbox } from "@/shared/components/Checkbox";
import { apiRequest, jsonRequest } from "@/shared/api/client";
import type { AuthSession } from "@/shared/api/types";
import { routes } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/cn";

type SignupType = "mentee" | "mentor";

const statusOptions = [
  { label: "학생", value: "student" },
  { label: "취업준비", value: "job_seeker" },
  { label: "이직/전환", value: "career_change" },
  { label: "재직중", value: "employed" },
  { label: "진로탐색", value: "career_exploration" },
  { label: "기타", value: "other" },
] as const;

type StatusSelection = (typeof statusOptions)[number]["value"];
type CurrentStatus = "student" | "job_seeker" | "career_change" | "employed" | "other";

function RequiredDot() {
  return (
    <Image
      src="/figma-assets/required-dot.svg"
      alt=""
      width={4}
      height={4}
      className="mt-1 size-1"
      draggable={false}
    />
  );
}

function FieldLabel({ children, required = false }: { children: string; required?: boolean }) {
  return (
    <span className="flex items-start gap-1 text-[16px] font-medium leading-[1.7] text-[#242424]">
      {children}
      {required ? <RequiredDot /> : null}
    </span>
  );
}

function SearchIcon() {
  return (
    <span className="relative block size-5">
      <Image
        src="/figma-assets/search-vector-circle.svg"
        alt=""
        width={16}
        height={16}
        className="absolute inset-[10%_20%_20%_10%] max-w-none"
        draggable={false}
      />
      <Image
        src="/figma-assets/search-vector-handle.svg"
        alt=""
        width={4}
        height={4}
        className="absolute inset-[70%_10%_10%_70%] max-w-none"
        draggable={false}
      />
    </span>
  );
}

function SignupTextField({
  label,
  placeholder = "",
  required = false,
  type = "text",
  rightIcon,
  rightText,
  name,
  value,
  onChange,
  minLength,
}: {
  label: string;
  placeholder?: string;
  required?: boolean;
  type?: string;
  rightIcon?: ReactNode;
  rightText?: string;
  name: string;
  value: string;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  minLength?: number;
}) {
  return (
    <label className="flex w-full flex-col gap-2">
      <FieldLabel required={required}>{label}</FieldLabel>
      <span className="flex h-[51px] w-full items-center rounded-lg border border-line-soft bg-white px-4">
        <input
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          minLength={minLength}
          required={required}
          className="min-w-0 flex-1 bg-transparent text-[16px] font-medium leading-[1.7] text-[#242424] outline-none placeholder:text-placeholder"
          placeholder={placeholder}
        />
        {rightText ? (
          <span className="shrink-0 text-[16px] font-medium leading-[1.7] text-placeholder">
            {rightText}
          </span>
        ) : null}
        {rightIcon ? <span className="ml-3 flex size-5 shrink-0 items-center justify-center">{rightIcon}</span> : null}
      </span>
    </label>
  );
}

function FileField({
  label,
  accept,
  fileName,
  onChange,
}: {
  label: string;
  accept: string;
  fileName?: string;
  onChange: (file: File | null) => void;
}) {
  return (
    <label className="flex w-full flex-col gap-2">
      <FieldLabel>{label}</FieldLabel>
      <span className="flex h-[51px] w-full cursor-pointer items-center gap-3 rounded-lg border border-line-soft bg-white px-4 text-[16px] font-medium leading-[1.7] text-placeholder">
        <Image
          src="/figma-assets/attachment-icon.svg"
          alt=""
          width={20}
          height={20}
          className="size-5 shrink-0"
          draggable={false}
        />
        <span className="truncate">{fileName ?? "파일 첨부"}</span>
        <input
          type="file"
          accept={accept}
          className="sr-only"
          onChange={(event) => onChange(event.target.files?.[0] ?? null)}
        />
      </span>
    </label>
  );
}

function RoleTabs({
  value,
  onChange,
}: {
  value: SignupType;
  onChange: (value: SignupType) => void;
}) {
  return (
    <div className="flex w-full gap-1.5 rounded-lg bg-[#f7f7f7] p-1.5">
      {[
        ["mentee", "멘티"],
        ["mentor", "멘토"],
      ].map(([type, label]) => {
        const selected = value === type;
        const disabled = type === "mentor";

        return (
          <button
            key={type}
            type="button"
            onClick={() => onChange(type as SignupType)}
            disabled={disabled}
            title={disabled ? "멘토 가입은 준비 중입니다." : undefined}
            className={cn(
              "flex min-w-0 flex-1 items-center justify-center rounded-lg px-5 py-1 text-[16px] font-medium leading-[1.7]",
              selected
                ? "bg-white text-[#242424] shadow-[0_1px_4px_rgba(88,88,88,0.12)]"
                : "text-placeholder",
              disabled && "cursor-not-allowed opacity-50",
            )}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

function StatusRadioGrid({ value, onChange }: { value: StatusSelection; onChange: (value: StatusSelection) => void }) {
  return (
    <fieldset className="flex w-full flex-col gap-2">
      <legend>
        <FieldLabel required>현재 상태</FieldLabel>
      </legend>
      <div className="grid w-full grid-cols-2 gap-x-5 gap-y-4 py-2 sm:grid-cols-3">
        {statusOptions.map((option) => {
          const checked = value === option.value;

          return (
            <button
              key={option.label}
              type="button"
              onClick={() => onChange(option.value)}
              className="flex items-center gap-1.5 text-left text-[16px] font-medium leading-[1.7] text-[#242424]"
            >
              <Image
                src={checked ? "/figma-assets/radio-select.svg" : "/figma-assets/radio-unselect.svg"}
                alt=""
                width={16}
                height={16}
                className="size-4 shrink-0"
                draggable={false}
              />
              {option.label}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export function SignupForm() {
  const router = useRouter();
  const [signupType, setSignupType] = useState<SignupType>("mentee");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [statusSelection, setStatusSelection] = useState<StatusSelection>("student");
  const [targetRole, setTargetRole] = useState("");
  const [resume, setResume] = useState<File | null>(null);
  const [portfolio, setPortfolio] = useState<File | null>(null);
  const [termsConsent, setTermsConsent] = useState(false);
  const [privacyConsent, setPrivacyConsent] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function uploadFile(path: string, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    await apiRequest(path, { method: "POST", body: formData });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!termsConsent || !privacyConsent) {
      setError("이용약관과 개인정보 수집에 동의해주세요.");
      return;
    }
    setError("");
    setIsSubmitting(true);
    try {
      const currentStatus: CurrentStatus = statusSelection === "career_exploration" ? "other" : statusSelection;
      await apiRequest<AuthSession>(
        "auth/signup",
        jsonRequest("POST", {
          email,
          password,
          name,
          currentStatus,
          targetRoles: targetRole ? [targetRole] : [],
          interestDomains: [],
          termsConsent,
          privacyConsent,
        }),
      );
      if (resume) await uploadFile("mentees/me/resume", resume);
      if (portfolio) await uploadFile("mentees/me/portfolio", portfolio);
      router.push(routes.chat);
      router.refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "회원가입에 실패했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="flex w-full max-w-[510px] flex-col gap-12" aria-label="회원가입" onSubmit={handleSubmit}>
      <h1 className="text-[23px] font-bold leading-[1.6] text-[#242424]">계정 만들기</h1>

      <RoleTabs value={signupType} onChange={setSignupType} />

      <div className="flex w-full flex-col gap-7">
        <SignupTextField name="name" value={name} onChange={(event) => setName(event.target.value)} label="이름" placeholder="이름을 적어주세요." required />
        <SignupTextField name="email" value={email} onChange={(event) => setEmail(event.target.value)} label="이메일" placeholder="이메일을 적어주세요." required type="email" />
        <SignupTextField
          name="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          label="비밀번호"
          placeholder="비밀번호를 적어주세요."
          required
          type="password"
          minLength={8}
          rightIcon={
            <Image
              src="/figma-assets/eye-off.svg"
              alt=""
              width={20}
              height={20}
              className="size-5"
              draggable={false}
            />
          }
        />
      </div>

      <div className="h-px w-full bg-[#e0e0e0]" />

      <div className="flex w-full flex-col gap-7">
        <StatusRadioGrid value={statusSelection} onChange={setStatusSelection} />
        <SignupTextField name="targetRole" value={targetRole} onChange={(event) => setTargetRole(event.target.value)} label="관심 직무" required rightIcon={<SearchIcon />} />

        <FileField label="이력서 및 경력기술서" accept=".pdf,.docx" fileName={resume?.name} onChange={setResume} />
        <FileField label="포트폴리오" accept=".pdf,.pptx" fileName={portfolio?.name} onChange={setPortfolio} />
      </div>

      <div className="flex w-full flex-col gap-5">
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-4">
            <Checkbox label="이용약관에 동의합니다." checked={termsConsent} onChange={(event) => setTermsConsent(event.target.checked)} />
            <Link href={routes.terms} className="text-[14px] font-medium text-brand-muted underline">보기</Link>
          </div>
          <div className="flex items-center justify-between gap-4">
            <Checkbox label="개인정보 수집에 동의합니다." checked={privacyConsent} onChange={(event) => setPrivacyConsent(event.target.checked)} />
            <Link href={routes.privacy} className="text-[14px] font-medium text-brand-muted underline">보기</Link>
          </div>
        </div>
        {error ? <p role="alert" className="text-[14px] text-red-600">{error}</p> : null}
        <Button type="submit" fullWidth disabled={isSubmitting}>
          {isSubmitting ? "가입 중..." : "멘티로 시작하기"}
        </Button>
        <p className="flex items-center justify-center gap-3 text-center text-[14px] font-medium leading-[1.4] text-brand-muted">
          계정이 이미 있으신가요?
          <Link href={routes.login} className="auth-action-link">
            로그인하기
          </Link>
        </p>
      </div>
    </form>
  );
}
