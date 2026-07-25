import type { QnaImagePosition } from "@/features/knowledge-asset/data/qna";

const positions: Record<QnaImagePosition, string> = {
  "top-left": "0% 0%",
  "top-center": "50% 0%",
  "top-right": "100% 0%",
  "bottom-left": "0% 100%",
  "bottom-center": "50% 100%",
  "bottom-right": "100% 100%",
};

export function QnaSpriteImage({
  position,
  className,
}: {
  position: QnaImagePosition;
  className?: string;
}) {
  return (
    <div
      className={className}
      style={{
        backgroundImage: "url('/figma-assets/qna-thumbnail-sprite.png')",
        backgroundPosition: positions[position],
        backgroundRepeat: "no-repeat",
        backgroundSize: "300% 200%",
      }}
    />
  );
}

export function RelatedSpriteImage({
  position,
  className,
}: {
  position: QnaImagePosition;
  className?: string;
}) {
  return (
    <div
      className={className}
      style={{
        backgroundImage: "url('/figma-assets/qna-related-sprite.png')",
        backgroundPosition: positions[position],
        backgroundRepeat: "no-repeat",
        backgroundSize: "200% 200%",
      }}
    />
  );
}
