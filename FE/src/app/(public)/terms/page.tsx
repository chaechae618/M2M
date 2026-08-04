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

export default function TermsPage() {
  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-16 sm:px-8">
      <Link href={routes.home} className="text-sm font-medium text-brand-muted underline">
        홈으로
      </Link>

      <h1 className="mt-6 text-2xl font-bold text-brand-text">이용약관</h1>
      <p className="mt-2 text-sm text-brand-muted">시행일: 2026년 8월 4일</p>

      <div className="mt-8 h-px w-full bg-[#e0e0e0]" />

      <article className="mt-10 flex flex-col gap-9">
        <Section title="제1조 (목적)">
          <p>
            이 약관은 M2M(이하 &ldquo;서비스&rdquo;)이 제공하는 AI 진로 멘토링 서비스의 이용조건과 절차, 이용자와
            서비스 운영자의 권리·의무 및 책임사항을 정하는 것을 목적으로 합니다.
          </p>
        </Section>

        <Section title="제2조 (서비스의 성격)">
          <p>
            1. 서비스는 이용자가 입력한 진로 고민을 질문으로 구조화하고, 축적된 멘토 답변 자산으로 검증한 뒤, 필요한
            경우 AI가 생성한 답변을 제공합니다.
          </p>
          <p>
            2. 서비스 내 &ldquo;멘토&rdquo;, &ldquo;멘토 매칭&rdquo;, &ldquo;멘토 추천&rdquo; 등으로 표시되는 기능은
            실제 인물과의 연결이나 실시간 상담을 의미하지 않습니다. 이용자가 확인하는 답변은 멘토의 맥락을 반영하여
            AI 언어모델이 그 자리에서 생성한 페르소나 응답이며, 실제 멘토가 직접 작성하거나 검수한 답변이 아닙니다.
          </p>
          <p>
            3. 서비스는 동아리 활동으로 제작된 시연용 프로젝트이며, 상용 서비스 수준의 가용성·정확성이나 지속적인
            운영을 보장하지 않습니다.
          </p>
        </Section>

        <Section title="제3조 (이용계약의 성립)">
          <p>
            가입 신청자가 이 약관 및 개인정보처리방침의 내용에 동의하고 이메일, 이름 등 필수 정보를 입력하여
            가입을 신청하면, 서비스가 이를 승낙함으로써 이용계약이 성립합니다.
          </p>
        </Section>

        <Section title="제4조 (이용자의 의무)">
          <p>이용자는 서비스 이용 중 다음 행위를 해서는 안 됩니다.</p>
          <ul className="list-disc pl-5">
            <li>가입 시 허위 정보를 등록하거나 타인의 정보를 도용하는 행위</li>
            <li>AI가 생성한 답변을 실제 멘토 또는 특정인의 발언으로 오인시켜 외부에 배포하는 행위</li>
            <li>본인이 게재 또는 업로드할 권리가 없는 이력서, 포트폴리오 등 자료를 업로드하는 행위</li>
            <li>서비스의 정상적인 운영을 방해하거나 다른 이용자의 이용을 방해하는 행위</li>
          </ul>
        </Section>

        <Section title="제5조 (게시물 및 답변의 자산화)">
          <p>
            1. 이용자가 작성한 질문과 이에 대해 생성된 AI 페르소나 답변은 서비스 품질 향상 및 향후 유사한 질문에
            대한 답변 자산으로 재사용될 수 있습니다.
          </p>
          <p>2. 자산화 과정에서는 이용자를 특정할 수 있는 정보를 제외하거나 비식별 처리하는 것을 원칙으로 합니다.</p>
        </Section>

        <Section title="제6조 (AI 답변의 한계 및 면책)">
          <p>
            1. AI 페르소나가 생성하는 답변은 참고용 정보이며, 실제 멘토의 검수를 거치지 않습니다. 진로, 취업,
            법률, 재무 등에 관한 전문적인 조언을 대체하지 않습니다.
          </p>
          <p>
            2. 서비스는 AI가 생성한 답변의 정확성이나 완전성을 보증하지 않으며, 이를 신뢰하여 발생한 손해에 대해
            책임을 지지 않습니다.
          </p>
        </Section>

        <Section title="제7조 (서비스의 변경 및 중단)">
          <p>
            서비스는 동아리 시연 목적의 프로젝트로, 사전 고지 없이 기능이 변경되거나 서비스 제공이 일시적 또는
            영구적으로 중단될 수 있습니다.
          </p>
        </Section>

        <Section title="제8조 (계약 해지 및 이용 제한)">
          <p>
            이용자는 마이페이지를 통해 언제든지 회원 탈퇴를 요청할 수 있습니다. 서비스는 이용자가 제4조를 위반한
            경우 사전 통지 후 이용을 제한할 수 있습니다.
          </p>
        </Section>

        <Section title="제9조 (약관의 변경)">
          <p>서비스는 필요한 경우 이 약관을 변경할 수 있으며, 변경 시 서비스 내 공지를 통해 안내합니다.</p>
        </Section>
      </article>

      <div className="mt-12 h-px w-full bg-[#e0e0e0]" />

      <p className="mt-6 text-sm text-brand-muted">
        개인정보 처리에 대한 안내는{" "}
        <Link href={routes.privacy} className="font-medium text-brand-text underline">
          개인정보처리방침
        </Link>
        을 확인해 주세요.
      </p>
    </main>
  );
}
