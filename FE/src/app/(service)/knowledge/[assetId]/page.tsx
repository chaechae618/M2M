import Image from "next/image";
import Link from "next/link";
import { QnaAvatar } from "@/features/knowledge-asset/components/QnaAvatar";
import { ArrowIcon, ScrapIcon, SearchIcon } from "@/features/knowledge-asset/components/QnaIcons";
import { RelatedArticleCard } from "@/features/knowledge-asset/components/RelatedArticleCard";
import { qnaDetail, relatedArticles } from "@/features/knowledge-asset/data/qna";
import { routes } from "@/shared/constants/routes";

export default function KnowledgeDetailPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[1040px] flex-col overflow-hidden px-5 pb-10 pt-20 sm:px-8 lg:px-0 lg:pt-[100px]">
      <header className="flex items-center justify-between">
        <Link href={routes.knowledge} aria-label="뒤로가기" className="flex size-10 items-center justify-center">
          <ArrowIcon direction="left" />
        </Link>
        <button type="button" aria-label="검색" className="flex size-10 items-center justify-center">
          <SearchIcon />
        </button>
      </header>

      <article className="mt-16 flex flex-col gap-9 lg:mt-[72px]">
        <section className="flex flex-col gap-4 border-b border-[#e0e0e0] pb-4">
          <div className="flex items-center justify-between gap-6">
            <h1 className="min-w-0 flex-1 text-[28px] font-bold leading-[1.4] text-black">
              {qnaDetail.title}
            </h1>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-4 text-[16px] font-normal leading-none text-brand-muted">
            <span>{qnaDetail.age}</span>
            <div className="flex items-center gap-5">
              <span>조회수 {qnaDetail.views}</span>
              <span className="flex items-center gap-2">
                <ScrapIcon filled />
                {qnaDetail.scraps}
              </span>
            </div>
          </div>
        </section>

        <section className="flex flex-col gap-10">
          <div className="text-[18px] font-medium leading-[1.6] text-[#242424]">
            {qnaDetail.body.map((paragraph) => (
              <p key={paragraph} className="mb-5 last:mb-0">
                {paragraph}
              </p>
            ))}
          </div>
          <div className="relative h-[240px] w-full overflow-hidden rounded bg-[#f2f2f2] sm:h-[389px]">
            <Image
              src="/figma-assets/qna-detail-hero.png"
              alt=""
              fill
              sizes="(min-width: 1040px) 1040px, 100vw"
              className="object-cover"
              priority
              draggable={false}
            />
          </div>
        </section>
      </article>

      <div className="mt-[72px] h-1.5 w-full bg-[#f7f7f7]" />

      <section className="mt-[72px] flex flex-col gap-9">
        <h2 className="text-[23px] font-bold leading-[1.6] text-brand-muted">답변</h2>
        <article className="flex flex-col gap-6">
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-3">
              <QnaAvatar color="#ffddb3" />
              <span className="text-[16px] font-medium leading-[1.7] text-[#242424]">프로덕트 매니저</span>
            </div>
            <span className="text-[16px] font-normal leading-none text-placeholder">2일 전</span>
          </div>
          <div>
            <p className="line-clamp-5 whitespace-pre-wrap text-[18px] font-medium leading-[1.6] text-[#242424]">
              {qnaDetail.answer}
            </p>
            <button type="button" className="mt-5 text-[17px] font-semibold leading-none text-placeholder">
              더보기
              <span className="mt-1 block h-px w-full bg-placeholder" />
            </button>
          </div>
        </article>
      </section>

      <div className="mt-[72px] h-1.5 w-full bg-[#f7f7f7]" />

      <section className="mt-[72px] flex flex-col gap-9">
        <h2 className="text-[23px] font-bold leading-[1.6] text-[#303030]">연관 게시글</h2>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {relatedArticles.map((article) => (
            <RelatedArticleCard key={article.title} article={article} />
          ))}
        </div>
      </section>
    </main>
  );
}
