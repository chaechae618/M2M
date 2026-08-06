export type QnaImagePosition = "top-left" | "top-center" | "top-right" | "bottom-left" | "bottom-center" | "bottom-right";

export type QnaArticle = {
  id: string;
  category: string;
  title: string;
  excerpt: string;
  mentor: string;
  age: string;
  scraps: number;
  saved: boolean;
  avatarColor: string;
  imagePosition: QnaImagePosition;
  imageUrl?: string;
};

export type RelatedArticle = {
  title: string;
  excerpt: string;
  scraps: number;
  imagePosition: QnaImagePosition;
  imageUrl?: string;
};
