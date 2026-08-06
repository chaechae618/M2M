import Image from "next/image";
import { ScrapIcon } from "@/features/knowledge-asset/components/QnaIcons";
import { RelatedSpriteImage } from "@/features/knowledge-asset/components/SpriteImage";
import type { RelatedArticle } from "@/features/knowledge-asset/data/qna";

export function RelatedArticleCard({ article }: { article: RelatedArticle }) {
  return (
    <article className="flex min-h-[168px] overflow-hidden rounded-lg border border-[#eeeeee] bg-white">
      {article.imageUrl ? (
        <div className="relative hidden w-[168px] shrink-0 bg-[#ebebeb] sm:block">
          <Image src={article.imageUrl} alt="" fill sizes="168px" className="object-cover" />
        </div>
      ) : (
        <RelatedSpriteImage position={article.imagePosition} className="hidden w-[168px] shrink-0 bg-[#ebebeb] sm:block" />
      )}
      <div className="flex min-w-0 flex-1 flex-col justify-between gap-2 px-5 py-6">
        <div className="flex min-w-0 flex-col gap-3">
          <h3 className="truncate text-[18px] font-bold leading-none tracking-[0.36px] text-brand-muted">
            {article.title}
          </h3>
          <p className="line-clamp-2 text-[16px] font-medium leading-[1.7] text-[#8d8d8d]">
            {article.excerpt}
          </p>
        </div>
        <div className="flex justify-end">
          <div className="flex items-center gap-2">
            <ScrapIcon />
            <span className="text-[14px] font-medium leading-[1.4] text-placeholder">{article.scraps}</span>
          </div>
        </div>
      </div>
    </article>
  );
}
