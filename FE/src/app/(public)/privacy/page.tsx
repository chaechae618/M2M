import Link from "next/link";
import type { ReactNode } from "react";
import { routes } from "@/shared/constants/routes";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-[17px] font-bold text-brand-text">{title}</h2>
      <div className="flex flex-col gap-2 text-sm leading-7 text-brand-muted">{children}</div>
    </section>
  );
}

export default function PrivacyPage() {
  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-16 sm:px-8">
      <Link href={routes.home} className="text-sm font-medium text-brand-muted underline">
        홈으로
      </Link>

      <h1 className="mt-6 text-2xl font-bold text-brand-text">개인정보처리방침</h1>
      <p className="mt-2 text-sm text-brand-muted">시행일: 2026년 8월 4일</p>

      <div className="mt-8 h-px w-full bg-[#e0e0e0]" />

      <p className="mt-10 text-sm leading-7 text-brand-muted">
        M2M(이하 &ldquo;서비스&rdquo;)은 이용자의 개인정보를 소중히 다루며, 개인정보 보호법 등 관련 법령을
        준수하기 위해 노력합니다. 다만 본 서비스는 동아리 활동으로 제작된 시연용 프로젝트로, 아래 내용은 그 목적에
        맞게 작성된 초안입니다.
      </p>

      <article className="mt-10 flex flex-col gap-9">
        <Section title="1. 수집하는 개인정보 항목">
          <p>서비스는 회원가입 및 AI 멘토링 제공을 위해 다음 정보를 수집합니다.</p>
          <ul className="list-disc pl-5">
            <li>필수: 이메일, 이름, 비밀번호(암호화 저장), 현재 상태(학생/구직/이직 등), 관심 직무·분야</li>
            <li>선택: 이력서 및 경력기술서, 포트폴리오 파일</li>
            <li>서비스 이용 중 생성: 상담에서 입력한 질문 내용, AI 페르소나 답변 기록</li>
          </ul>
        </Section>

        <Section title="2. 개인정보의 수집 및 이용 목적">
          <ul className="list-disc pl-5">
            <li>회원 식별, 로그인 및 계정 관리</li>
            <li>진로 고민의 질문 구조화, 기존 답변 자산 검증, AI 멘토 페르소나 매칭 및 답변 생성</li>
            <li>이력서·포트폴리오 내용을 반영한 맞춤 답변 제공</li>
            <li>답변 자산 축적을 통한 서비스 품질 개선</li>
          </ul>
        </Section>

        <Section title="3. 처리 위탁 및 제3자 제공">
          <p>
            이용자가 입력한 질문과 업로드한 이력서·포트폴리오의 내용은 답변 생성을 위해 OpenAI 등 외부 AI
            언어모델(LLM) API로 전송되어 처리될 수 있습니다.
          </p>
          <p>위 처리는 답변 생성 목적으로만 이루어지며, 이용자의 별도 동의 없이 광고 등 다른 목적으로 제3자에게 제공하지 않습니다.</p>
        </Section>

        <Section title="4. 개인정보의 보유 및 이용 기간">
          <p>회원 탈퇴 시 지체 없이 파기하는 것을 원칙으로 합니다.</p>
          <p>본 서비스는 시연용 프로젝트로, 별도의 장기 백업·로그 보관 정책은 운영하지 않습니다.</p>
        </Section>

        <Section title="5. 이용자의 권리">
          <p>이용자는 언제든지 자신의 개인정보에 대한 열람, 정정, 삭제, 처리정지를 요청할 수 있습니다.</p>
          <p>마이페이지에서 이력서·포트폴리오 삭제 및 회원 탈퇴를 직접 진행할 수 있으며, 일부 기능은 준비 중일 수 있습니다.</p>
        </Section>

        <Section title="6. 개인정보의 파기">
          <p>
            회원 탈퇴, 서비스 종료 등으로 개인정보가 불필요하게 된 때에는 지체 없이 파기하며, 전자적 파일 형태의
            정보는 복구할 수 없는 방법으로 삭제합니다.
          </p>
        </Section>

        <Section title="7. 안전성 확보조치">
          <p>비밀번호 암호화 저장, 접근 권한 제한 등 최소한의 보호조치를 적용하고 있습니다.</p>
          <p>다만 본 서비스는 상용 서비스 수준의 보안 인증을 받지 않은 시연용 프로젝트임을 안내드립니다.</p>
        </Section>

        <Section title="8. 문의처">
          <p>개인정보 처리와 관련한 문의는 서비스 운영자 이메일로 연락해 주시기 바랍니다.</p>
        </Section>
      </article>

      <div className="mt-12 h-px w-full bg-[#e0e0e0]" />

      <p className="mt-6 text-sm text-brand-muted">
        서비스 이용 조건에 대한 안내는{" "}
        <Link href={routes.terms} className="font-medium text-brand-text underline">
          이용약관
        </Link>
        을 확인해 주세요.
      </p>
    </main>
  );
}
