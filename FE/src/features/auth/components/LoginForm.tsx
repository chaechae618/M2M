"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/shared/components/Button";
import { Checkbox } from "@/shared/components/Checkbox";
import { Input } from "@/shared/components/Input";
import { apiRequest, jsonRequest } from "@/shared/api/client";
import type { AuthSession } from "@/shared/api/types";
import { routes } from "@/shared/constants/routes";

function ProfileIcon() {
  return (
    <span className="relative block size-5 overflow-visible">
      <Image
        src="/figma-assets/profile-vector.svg"
        alt=""
        width={19}
        height={19}
        className="absolute inset-[6.25%] h-[87.5%] w-[87.5%] max-w-none"
        draggable={false}
      />
      <Image
        src="/figma-assets/profile-vector-lower.svg"
        alt=""
        width={15}
        height={4}
        className="absolute bottom-[22.24%] left-[16.18%] h-[12.45%] w-[67.63%] max-w-none"
        draggable={false}
      />
      <Image
        src="/figma-assets/profile-vector-head.svg"
        alt=""
        width={8.4}
        height={8.4}
        className="absolute left-[32.5%] top-[23.75%] h-[35%] w-[35%] max-w-none"
        draggable={false}
      />
    </span>
  );
}

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await apiRequest<AuthSession>("auth/login", jsonRequest("POST", { email, password }));
      router.push(routes.chat);
      router.refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "로그인에 실패했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="w-full max-w-[clamp(440px,23.5vw,480px)]" aria-label="로그인" onSubmit={handleSubmit}>
      <div className="mb-[60px] text-center text-[20px] font-semibold leading-[1.55] text-brand-muted max-sm:mb-10 max-sm:text-[18px]">
        <h1>안녕하세요.</h1>
        <p>고민을 질문으로, 질문을 답변으로 바꿔보세요!</p>
      </div>

      <div className="space-y-7">
        <label className="block">
          <span className="mb-2 block text-[16px] font-medium leading-[1.7] text-[#242424]">
            이메일
          </span>
          <Input
            name="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="username"
            placeholder="이메일을 적어주세요."
            leftIcon={<ProfileIcon />}
          />
        </label>

        <label className="block">
          <span className="mb-2 flex flex-wrap items-center justify-between gap-2 text-[16px] font-medium leading-[1.7] text-[#242424]">
            <span>비밀번호</span>
            <span className="text-[15px] font-semibold leading-[1.4] text-[#9e9e9e]">
              비밀번호를 잊어버리셨나요?
            </span>
          </span>
          <Input
            name="password"
            type={isPasswordVisible ? "text" : "password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
            placeholder="비밀번호를 적어주세요."
            leftIconSrc="/figma-assets/lock-icon.svg"
            rightIconSrc={isPasswordVisible ? "/figma-assets/eye-fill.svg" : "/figma-assets/eye-off.svg"}
            onRightIconClick={() => setIsPasswordVisible((value) => !value)}
            rightIconLabel={isPasswordVisible ? "비밀번호 숨기기" : "비밀번호 보기"}
          />
        </label>
      </div>

      <div className="mt-7">
        <Checkbox label="로그인 상태 유지" defaultChecked />
      </div>

      <div className="mt-7">
        {error ? <p role="alert" className="mb-3 text-[14px] text-red-600">{error}</p> : null}
        <Button type="submit" fullWidth className="flex" disabled={isSubmitting}>
          {isSubmitting ? "로그인 중..." : "로그인하기"}
        </Button>
      </div>

      <p className="auth-signup-row flex items-center justify-center gap-1 text-center text-[14px] font-medium leading-[1.4] text-brand-muted">
        계정이 없으신가요?
        <Link href={routes.signup} className="auth-action-link text-[15px] font-semibold">
          계정 만들기
        </Link>
      </p>
    </form>
  );
}
