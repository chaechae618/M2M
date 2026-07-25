import Image from "next/image";

export function QnaAvatar({ color }: { color: string }) {
  return (
    <span
      className="relative flex size-8 shrink-0 items-center justify-center rounded-full"
      style={{ backgroundColor: color }}
    >
      <Image
        src="/figma-assets/qna-person.svg"
        alt=""
        width={14}
        height={16}
        className="h-4 w-3.5"
        draggable={false}
      />
    </span>
  );
}
