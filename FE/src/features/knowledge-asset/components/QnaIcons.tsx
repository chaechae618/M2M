import Image from "next/image";

export function SearchIcon({ size = 24 }: { size?: number }) {
  return (
    <span className="relative block shrink-0" style={{ width: size, height: size }}>
      <Image
        src="/figma-assets/qna-search-circle.svg"
        alt=""
        width={17}
        height={17}
        className="absolute inset-[10%_20%_20%_10%] max-w-none"
        draggable={false}
      />
      <Image
        src="/figma-assets/qna-search-handle.svg"
        alt=""
        width={5}
        height={5}
        className="absolute inset-[70%_10%_10%_70%] max-w-none"
        draggable={false}
      />
    </span>
  );
}

export function ScrapIcon({ filled = false, size = 20 }: { filled?: boolean; size?: number }) {
  return (
    <Image
      src={filled ? "/figma-assets/qna-scrap-filled.svg" : "/figma-assets/qna-scrap-stroke.svg"}
      alt=""
      width={size}
      height={size}
      className="shrink-0"
      draggable={false}
    />
  );
}

export function ArrowIcon({ direction }: { direction: "left" | "right" }) {
  return (
    <Image
      src={direction === "left" ? "/figma-assets/qna-arrow-left.svg" : "/figma-assets/qna-arrow-right.svg"}
      alt=""
      width={20}
      height={20}
      className="size-5 shrink-0"
      draggable={false}
    />
  );
}
