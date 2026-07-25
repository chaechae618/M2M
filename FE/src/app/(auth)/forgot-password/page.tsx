import Link from "next/link";
import { routes } from "@/shared/constants/routes";

export default function ForgotPasswordPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-white px-6">
      <section className="w-full max-w-md text-center">
        <h1 className="text-2xl font-bold text-brand-text">비밀번호 찾기</h1>
        <p className="mt-3 text-sm text-brand-muted">
          이메일 인증 기반 재설정 화면으로 이어질 자리입니다.
        </p>
        <Link
          href={routes.login}
          className="mt-8 inline-flex h-11 items-center justify-center rounded-lg bg-brand-yellow px-5 text-sm font-bold text-zinc-950"
        >
          로그인으로 돌아가기
        </Link>
      </section>
    </main>
  );
}
