import Image from "next/image";
import Link from "next/link";
import { QnaAvatar } from "@/features/knowledge-asset/components/QnaAvatar";
import { ScrapIcon } from "@/features/knowledge-asset/components/QnaIcons";
import { QnaSpriteImage } from "@/features/knowledge-asset/components/SpriteImage";
import type { QnaArticle } from "@/features/knowledge-asset/data/qna";

export function QnaArticleItem({ article }: { article: QnaArticle }) {
  return (
    <article className="flex w-full gap-5 border-b border-[#e0e0e0] pb-10 last:border-b-0 md:gap-9">
      <Link href={`/knowledge/${article.id}`} className="min-w-0 flex-1">
        <div className="flex min-w-0 flex-col gap-4">
          <p className="truncate text-[15px] font-medium leading-none text-accent-orange">
            {article.category}
          </p>
          <h2 className="truncate text-[23px] font-bold leading-[1.6] text-[#212121] max-md:text-[20px]">
            {article.title}
          </h2>
          <p className="line-clamp-2 text-[16px] font-medium leading-[1.7] text-[#7a7a7a]">
            {article.excerpt}
          </p>
        </div>

        <div className="mt-4 flex items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-5">
            <div className="flex min-w-0 items-center gap-3">
              <QnaAvatar color={article.avatarColor} />
              <p className="truncate text-[16px] font-medium leading-[1.7] text-[#242424]">
                {article.mentor}
              </p>
            </div>
            <p className="shrink-0 text-[16px] font-normal leading-none text-placeholder">{article.age}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <ScrapIcon filled={article.saved} />
            <span className="text-[14px] font-medium leading-[1.4] text-[#7a7a7a]">{article.scraps}</span>
          </div>
        </div>
      </Link>

      <Link href={`/knowledge/${article.id}`} className="hidden shrink-0 sm:block">
        {article.imageUrl ? (
          <div className="relative h-[125px] w-[125px] overflow-hidden rounded bg-[#f2f2f2]">
            <Image src={article.imageUrl} alt="" fill sizes="125px" className="object-cover" />
          </div>
        ) : (
          <QnaSpriteImage position={article.imagePosition} className="h-[125px] w-[125px] overflow-hidden rounded bg-[#f2f2f2]" />
        )}
      </Link>
    </article>
  );
}
