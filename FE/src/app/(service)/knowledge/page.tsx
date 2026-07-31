"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { QnaArticleItem } from "@/features/knowledge-asset/components/QnaArticleItem";
import { ArrowIcon, SearchIcon } from "@/features/knowledge-asset/components/QnaIcons";
import { toQnaArticle, type QnaPostList } from "@/features/knowledge-asset/api/qna";
import { ApiError, apiRequest } from "@/shared/api/client";
import { routes } from "@/shared/constants/routes";

export default function KnowledgeBoardPage() {
  const router = useRouter();
  const [data, setData] = useState<QnaPostList | null>(null);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ page: String(page), limit: "5" });
    if (submittedQuery) params.set("query", submittedQuery);
    apiRequest<QnaPostList>(`qna/posts?${params}`)
      .then((result) => {
      setError("");
      setData(result);
      })
      .catch((requestError) => {
        if (requestError instanceof ApiError && requestError.status === 401) {
          router.replace(routes.login);
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "게시글을 불러오지 못했습니다.");
      });
  }, [page, router, submittedQuery]);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setSubmittedQuery(query.trim());
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[1040px] flex-col px-5 pb-32 pt-20 sm:px-8 lg:px-0 lg:pt-[100px]">
      <header className="flex items-center justify-between gap-5">
        <h1 className="text-[28px] font-bold leading-[1.4] text-black">큐엔에이</h1>
        {searchOpen ? (
          <form onSubmit={submitSearch} className="flex w-full max-w-sm items-center gap-2">
            <input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="검색어를 입력해주세요." className="h-10 min-w-0 flex-1 border-b border-[#d8d8d8] px-2 text-[15px] outline-none focus:border-[#ffad00]" />
            <button type="submit" aria-label="검색" className="flex size-10 items-center justify-center"><SearchIcon /></button>
          </form>
        ) : (
          <button type="button" aria-label="검색 열기" onClick={() => setSearchOpen(true)} className="flex size-10 items-center justify-center"><SearchIcon /></button>
        )}
      </header>

      {error ? <p role="alert" className="mt-12 text-[15px] text-red-600">{error}</p> : null}
      {!data && !error ? <p className="mt-16 text-[16px] text-[#7a7a7a]">게시글을 불러오는 중...</p> : null}

      <section className="mt-16 flex flex-col gap-10 lg:mt-[68px]">
        {data?.items.map((post, index) => <QnaArticleItem key={post.id} article={toQnaArticle(post, index)} />)}
        {data && data.items.length === 0 ? <p className="py-20 text-center text-[16px] text-[#9e9e9e]">아직 등록된 게시글이 없습니다.</p> : null}
      </section>

      {data && data.pagination.totalPages > 1 ? (
        <nav className="mt-[100px] flex items-center justify-center gap-[25px]" aria-label="페이지 넘기기">
          <button type="button" aria-label="이전 페이지" disabled={!data.pagination.hasPrev} onClick={() => setPage((value) => value - 1)} className="flex size-5 items-center justify-center disabled:opacity-30"><ArrowIcon direction="left" /></button>
          <div className="flex items-center gap-5 text-[16px] font-normal leading-none">
            {Array.from({ length: data.pagination.totalPages }, (_, index) => index + 1).slice(0, 5).map((pageNumber) => (
              <button key={pageNumber} type="button" onClick={() => setPage(pageNumber)} className={pageNumber === page ? "text-[#242424]" : "text-line-soft"}>{pageNumber}</button>
            ))}
          </div>
          <button type="button" aria-label="다음 페이지" disabled={!data.pagination.hasNext} onClick={() => setPage((value) => value + 1)} className="flex size-5 items-center justify-center disabled:opacity-30"><ArrowIcon direction="right" /></button>
        </nav>
      ) : null}
    </main>
  );
}
