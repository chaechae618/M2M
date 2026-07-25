import { QnaArticleItem } from "@/features/knowledge-asset/components/QnaArticleItem";
import { ArrowIcon, SearchIcon } from "@/features/knowledge-asset/components/QnaIcons";
import { qnaArticles } from "@/features/knowledge-asset/data/qna";

export default function KnowledgeBoardPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[1040px] flex-col px-5 pb-10 pt-20 sm:px-8 lg:px-0 lg:pt-[100px]">
      <header className="flex items-center justify-between">
        <h1 className="text-[28px] font-bold leading-[1.4] text-black">큐엔에이</h1>
        <button type="button" aria-label="검색" className="flex size-10 items-center justify-center">
          <SearchIcon />
        </button>
      </header>

      <section className="mt-16 flex flex-col gap-10 lg:mt-[68px]">
        {qnaArticles.map((article) => (
          <QnaArticleItem key={article.id} article={article} />
        ))}
      </section>

      <nav className="mt-[100px] flex items-center justify-center gap-[25px]" aria-label="페이지 넘기기">
        <button type="button" aria-label="이전 페이지" className="flex size-5 items-center justify-center">
          <ArrowIcon direction="left" />
        </button>
        <div className="flex items-center gap-5 text-[16px] font-normal leading-none">
          {[1, 2, 3, 4, 5].map((page) => (
            <button
              key={page}
              type="button"
              className={page === 1 ? "text-[#242424]" : "text-line-soft"}
            >
              {page}
            </button>
          ))}
        </div>
        <button type="button" aria-label="다음 페이지" className="flex size-5 items-center justify-center">
          <ArrowIcon direction="right" />
        </button>
      </nav>
    </main>
  );
}
