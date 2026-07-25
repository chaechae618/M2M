import Image from "next/image";
import Link from "next/link";
import { routes } from "@/shared/constants/routes";

export function AuthBrandPanel() {
  return (
    <aside className="auth-brand-panel relative flex min-h-[300px] w-full overflow-hidden rounded-2xl bg-[#eef5de] sm:min-h-[420px] lg:h-full lg:min-h-0 lg:w-[min(100%,clamp(calc((100vh-24px)*0.696),48.333vw,860px))]">
      <Image
        src="/figma-assets/auth-bg.png"
        alt=""
        fill
        sizes="(min-width: 1024px) min(50vw, clamp(calc((100vh - 24px) * 0.696), 48.333vw, 860px)), 100vw"
        className="absolute inset-0 h-full w-full object-cover"
        draggable={false}
        priority
      />
      <div className="absolute inset-0 rounded-2xl bg-[rgba(217,255,161,0.16)]" />

      <div className="relative z-10 flex w-full flex-col justify-between px-6 py-5 sm:px-8 sm:py-8 lg:px-12 lg:py-8">
        <div aria-hidden="true" className="hidden h-[27px] lg:block" />

        <div className="mx-auto flex w-full flex-col items-center gap-3">
          <div className="auth-brand-logo-row flex w-full min-w-0 items-center justify-center">
            <div className="auth-brand-character relative shrink-0">
              <Image
                src="/figma-assets/auth-character.svg"
                alt=""
                width={70.934}
                height={68.878}
                className="absolute left-[-21.49%] top-[-24.47%] h-[151.25%] w-[147.78%] max-w-none"
                draggable={false}
              />
            </div>
            <Image
              src="/figma-assets/auth-wordmark.svg"
              alt="mento to mentee"
              width={459}
              height={38}
              className="auth-brand-wordmark"
              draggable={false}
            />
          </div>
          <p className="auth-brand-slogan w-full text-center font-semibold leading-[1.6] text-[rgba(80,74,76,0.7)]">
            막연한 고민에서 나에게 맞는 답변으로
          </p>
        </div>

        <nav className="flex h-[30px] items-end justify-between text-center text-[clamp(13px,1.111vw,16px)] font-normal leading-none text-brand-muted">
          <Link href={routes.privacy}>개인정보처리방침</Link>
          <Link href={routes.terms}>이용약관</Link>
        </nav>
      </div>
    </aside>
  );
}
