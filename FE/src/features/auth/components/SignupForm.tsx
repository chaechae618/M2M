"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/shared/components/Button";
import { routes } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/cn";

type SignupType = "mentee" | "mentor";

const statusOptions = ["학생", "취업준비", "이직/전환", "재직중", "진로탐색", "기타"];

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
}: {
  label: string;
  placeholder?: string;
  required?: boolean;
  type?: string;
  rightIcon?: React.ReactNode;
  rightText?: string;
}) {
  return (
    <label className="flex w-full flex-col gap-2">
      <FieldLabel required={required}>{label}</FieldLabel>
      <span className="flex h-[51px] w-full items-center rounded-lg border border-line-soft bg-white px-4">
        <input
          type={type}
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

function FileField({ label }: { label: string }) {
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
        파일 첨부
        <input type="file" className="sr-only" />
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

        return (
          <button
            key={type}
            type="button"
            onClick={() => onChange(type as SignupType)}
            className={cn(
              "flex min-w-0 flex-1 items-center justify-center rounded-lg px-5 py-1 text-[16px] font-medium leading-[1.7]",
              selected
                ? "bg-white text-[#242424] shadow-[0_1px_4px_rgba(88,88,88,0.12)]"
                : "text-placeholder",
            )}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

function StatusRadioGrid() {
  const [selected, setSelected] = useState(statusOptions[0]);

  return (
    <fieldset className="flex w-full flex-col gap-2">
      <legend>
        <FieldLabel required>현재 상태</FieldLabel>
      </legend>
      <div className="grid w-full grid-cols-2 gap-x-5 gap-y-4 py-2 sm:grid-cols-3">
        {statusOptions.map((option) => {
          const checked = selected === option;

          return (
            <button
              key={option}
              type="button"
              onClick={() => setSelected(option)}
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
              {option}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export function SignupForm() {
  const [signupType, setSignupType] = useState<SignupType>("mentee");
  const isMentor = signupType === "mentor";

  return (
    <form className="flex w-full max-w-[510px] flex-col gap-12" aria-label="회원가입">
      <h1 className="text-[23px] font-bold leading-[1.6] text-[#242424]">계정 만들기</h1>

      <RoleTabs value={signupType} onChange={setSignupType} />

      <div className="flex w-full flex-col gap-7">
        <SignupTextField label="이름" placeholder="이름을 적어주세요." required />
        <SignupTextField label="이메일" placeholder="이메일을 적어주세요." required />
        <SignupTextField
          label="비밀번호"
          placeholder="비밀번호를 적어주세요."
          required
          type="password"
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
        {isMentor ? (
          <>
            <SignupTextField label="총 경력" required rightText="년" />
            <SignupTextField label="전문 직무" required rightIcon={<SearchIcon />} />
          </>
        ) : (
          <>
            <StatusRadioGrid />
            <SignupTextField label="관심 직무" required rightIcon={<SearchIcon />} />
          </>
        )}

        <FileField label="이력서 및 경력기술서" />
        <FileField label="포트폴리오" />
      </div>

      <div className="flex w-full flex-col gap-5">
        <Button type="submit" fullWidth>
          {isMentor ? "멘토로 시작하기" : "멘티로 시작하기"}
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
