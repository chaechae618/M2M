"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { QnaAvatar } from "@/features/knowledge-asset/components/QnaAvatar";
import { ArrowIcon, ScrapIcon, SearchIcon } from "@/features/knowledge-asset/components/QnaIcons";
import { RelatedArticleCard } from "@/features/knowledge-asset/components/RelatedArticleCard";
import { apiAssetUrl, ApiError, apiRequest, jsonRequest } from "@/shared/api/client";
import { relativeDate, type QnaComment, type QnaPost, type QnaPostList } from "@/features/knowledge-asset/api/qna";
import type { RelatedArticle } from "@/features/knowledge-asset/data/qna";
import { routes } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/cn";

export default function KnowledgeDetailPage() {
  const { assetId } = useParams<{ assetId: string }>();
  const router = useRouter();
  const [post, setPost] = useState<QnaPost | null>(null);
  const [related, setRelated] = useState<RelatedArticle[]>([]);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([
      apiRequest<QnaPost>(`qna/posts/${assetId}`),
      apiRequest<QnaPostList>("qna/posts?limit=5"),
    ]).then(([detail, list]) => {
      setPost(detail);
      setRelated(list.items.filter((item) => item.id !== detail.id).slice(0, 4).map((item, index) => ({
        title: item.title,
        excerpt: item.content,
        scraps: 0,
        imagePosition: (["top-left", "top-right", "bottom-left", "bottom-right"] as const)[index],
        imageUrl: apiAssetUrl(item.images[0]?.url) ?? undefined,
      })));
    }).catch((requestError) => {
      if (requestError instanceof ApiError && requestError.status === 401) {
        router.replace(routes.login);
        return;
      }
      setError(requestError instanceof Error ? requestError.message : "게시글을 불러오지 못했습니다.");
    });
  }, [assetId, router]);

  async function submitComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!comment.trim() || !post) return;
    setIsSubmitting(true);
    setError("");
    try {
      const created = await apiRequest<QnaComment>(
        `qna/posts/${post.id}/comments`,
        jsonRequest("POST", { content: comment.trim(), anonymous: false }),
      );
      setPost((current) => current ? { ...current, comments: [...(current.comments ?? []), created], commentCount: current.commentCount + 1 } : current);
      setComment("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "답변을 등록하지 못했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!post) {
    return <main className="mx-auto min-h-screen w-full max-w-[1040px] px-5 pt-20 text-[16px] text-[#7a7a7a]">{error || "게시글을 불러오는 중..."}</main>;
  }

  const heroImage = apiAssetUrl(post.images[0]?.url);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[1040px] flex-col overflow-hidden px-5 pb-32 pt-20 sm:px-8 lg:px-0 lg:pt-[100px]">
      <header className="flex items-center justify-between">
        <Link href={routes.knowledge} aria-label="뒤로가기" className="flex size-10 items-center justify-center"><ArrowIcon direction="left" /></Link>
        <Link href={routes.knowledge} aria-label="검색" className="flex size-10 items-center justify-center"><SearchIcon /></Link>
      </header>

      {error ? <p role="alert" className="mt-6 text-[14px] text-red-600">{error}</p> : null}

      <article className="mt-16 flex flex-col gap-9 lg:mt-[72px]">
        <section className="flex flex-col gap-4 border-b border-[#e0e0e0] pb-4">
          <p className="text-[15px] font-medium text-accent-orange">{post.category}</p>
          <h1 className="text-[28px] font-bold leading-[1.4] text-black">{post.title}</h1>
          <div className="flex flex-wrap items-center justify-between gap-4 text-[16px] font-normal leading-none text-brand-muted">
            <span>{relativeDate(post.createdAt)} · {post.author.name}</span>
            <div className="flex items-center gap-5"><span>조회수 {post.viewCount.toLocaleString()}</span><span className="flex items-center gap-2"><ScrapIcon filled={false} />0</span></div>
          </div>
        </section>

        <section className="flex flex-col gap-10">
          <div className="whitespace-pre-wrap text-[18px] font-medium leading-[1.6] text-[#242424]">{post.content}</div>
          {heroImage ? (
            <div className="relative h-[240px] w-full overflow-hidden rounded bg-[#f2f2f2] sm:h-[389px]">
              <Image src={heroImage} alt="" fill sizes="(min-width: 1040px) 1040px, 100vw" className="object-cover" priority />
            </div>
          ) : null}
        </section>
      </article>

      <div className="mt-[72px] h-1.5 w-full bg-[#f7f7f7]" />

      <section className="mt-[72px] flex flex-col gap-9">
        <h2 className="text-[23px] font-bold leading-[1.6] text-brand-muted">답변 {post.commentCount}</h2>
        {post.comments?.map((item, index) => (
          <CommentItem key={item.id} item={item} avatarColor={index % 2 ? "#cdd6d8" : "#ffddb3"} />
        ))}
        {!post.comments?.length ? <p className="text-[16px] text-[#9e9e9e]">아직 등록된 답변이 없습니다.</p> : null}
        <form onSubmit={submitComment} className="flex flex-col gap-3">
          <textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder="답변을 입력해주세요." maxLength={5000} className="min-h-28 resize-y rounded-lg border border-[#e0e0e0] p-4 text-[16px] outline-none focus:border-[#ffad00]" />
          <button type="submit" disabled={isSubmitting || !comment.trim()} className="self-end rounded-lg bg-[#ffd60a] px-4 py-2 text-[14px] font-semibold text-[#51431f] disabled:opacity-40">{isSubmitting ? "등록 중..." : "답변 등록"}</button>
        </form>
      </section>

      {related.length ? (
        <>
          <div className="mt-[72px] h-1.5 w-full bg-[#f7f7f7]" />
          <section className="mt-[72px] flex flex-col gap-9">
            <h2 className="text-[23px] font-bold leading-[1.6] text-[#303030]">연관 게시글</h2>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">{related.map((article) => <RelatedArticleCard key={article.title} article={article} />)}</div>
          </section>
        </>
      ) : null}
    </main>
  );
}

function CommentItem({ item, avatarColor }: { item: QnaComment; avatarColor: string }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isOverflowing, setIsOverflowing] = useState(false);
  const contentRef = useRef<HTMLParagraphElement>(null);

  useLayoutEffect(() => {
    const el = contentRef.current;
    if (el) setIsOverflowing(el.scrollHeight > el.clientHeight + 1);
  }, [item.content]);

  return (
    <article className="flex flex-col gap-5 border-b border-[#eeeeee] pb-8">
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-3"><QnaAvatar color={avatarColor} /><span className="text-[16px] font-medium leading-[1.7] text-[#242424]">{item.author.name}</span></div>
        <span className="text-[16px] font-normal leading-none text-placeholder">{relativeDate(item.createdAt)}</span>
      </div>
      <div className="flex flex-col gap-3">
        <p
          ref={contentRef}
          className={cn(
            "whitespace-pre-wrap text-[18px] font-medium leading-[1.6] text-[#242424]",
            !isExpanded && "line-clamp-5",
          )}
        >
          {item.content}
        </p>
        {isOverflowing ? (
          <button
            type="button"
            onClick={() => setIsExpanded((value) => !value)}
            className="self-start text-[15px] font-semibold text-[#9e9e9e]"
          >
            {isExpanded ? "접기" : "더보기"}
          </button>
        ) : null}
      </div>
    </article>
  );
}
