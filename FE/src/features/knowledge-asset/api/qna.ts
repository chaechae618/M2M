import { apiAssetUrl } from "@/shared/api/client";
import type { Pagination } from "@/shared/api/types";
import type { QnaArticle } from "@/features/knowledge-asset/data/qna";

export type QnaAuthor = { id: string | null; name: string; anonymous: boolean };
export type QnaComment = {
  id: string;
  content: string;
  author: QnaAuthor;
  createdAt: string;
  updatedAt?: string;
};
export type QnaPost = {
  id: string;
  category: string;
  title: string;
  content: string;
  author: QnaAuthor;
  images: Array<{ imageId: string; url: string }>;
  viewCount: number;
  commentCount: number;
  createdAt: string;
  updatedAt: string;
  comments?: QnaComment[];
};
export type QnaPostList = { items: QnaPost[]; pagination: Pagination };

const avatarColors = ["#cdd6d8", "#ffddb3", "#f1bbbc", "#bdd99b", "#f9e2ae"];
const imagePositions = ["bottom-center", "top-center", "top-right", "bottom-left", "bottom-right"] as const;

export function relativeDate(value: string) {
  const elapsed = Math.max(0, Date.now() - new Date(value).getTime());
  const days = Math.floor(elapsed / 86_400_000);
  if (days === 0) return "오늘";
  if (days < 30) return `${days}일 전`;
  if (days < 365) return `${Math.floor(days / 30)}달 전`;
  return `${Math.floor(days / 365)}년 전`;
}

export function toQnaArticle(post: QnaPost, index = 0): QnaArticle {
  return {
    id: post.id,
    category: post.category,
    title: post.title,
    excerpt: post.content,
    mentor: post.author.name,
    age: relativeDate(post.createdAt),
    scraps: 0,
    saved: false,
    avatarColor: avatarColors[index % avatarColors.length],
    imagePosition: imagePositions[index % imagePositions.length],
    imageUrl: apiAssetUrl(post.images[0]?.url) ?? undefined,
  };
}
