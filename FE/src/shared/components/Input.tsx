import Image from "next/image";
import type { InputHTMLAttributes, ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  leftIcon?: ReactNode;
  leftIconSrc?: string;
  rightIcon?: ReactNode;
  rightIconSrc?: string;
  onRightIconClick?: () => void;
  rightIconLabel?: string;
};

export function Input({
  className,
  leftIcon,
  leftIconSrc,
  rightIcon,
  rightIconSrc,
  onRightIconClick,
  rightIconLabel,
  ...props
}: InputProps) {
  return (
    <div className="relative">
      {leftIconSrc ? (
        <span className="pointer-events-none absolute left-4 top-1/2 flex size-5 -translate-y-1/2 items-center justify-center">
          <Image
            src={leftIconSrc}
            alt=""
            width={20}
            height={20}
            className="block size-5"
            draggable={false}
          />
        </span>
      ) : leftIcon ? (
        <span className="pointer-events-none absolute left-4 top-1/2 flex size-5 -translate-y-1/2 items-center justify-center text-placeholder">
          {leftIcon}
        </span>
      ) : null}
      <input
        className={cn(
          "h-[51px] w-full rounded-lg border border-line-soft bg-white text-[16px] font-medium leading-[1.7] text-[#242424] outline-none transition placeholder:text-placeholder focus:border-brand-yellow focus:ring-2 focus:ring-brand-yellow/20",
          leftIcon || leftIconSrc ? "pl-12" : "pl-4",
          rightIcon || rightIconSrc ? "pr-12" : "pr-4",
          className,
        )}
        {...props}
      />
      {rightIconSrc ? (
        onRightIconClick ? (
          <button
            type="button"
            onClick={onRightIconClick}
            aria-label={rightIconLabel}
            className="absolute right-4 top-1/2 flex size-5 -translate-y-1/2 items-center justify-center"
          >
            <Image
              src={rightIconSrc}
              alt=""
              width={20}
              height={20}
              className="block size-5"
              draggable={false}
            />
          </button>
        ) : (
          <span className="absolute right-4 top-1/2 flex size-5 -translate-y-1/2 items-center justify-center">
            <Image
              src={rightIconSrc}
              alt=""
              width={20}
              height={20}
              className="block size-5"
              draggable={false}
            />
          </span>
        )
      ) : rightIcon ? (
        onRightIconClick ? (
          <button
            type="button"
            onClick={onRightIconClick}
            aria-label={rightIconLabel}
            className="absolute right-4 top-1/2 flex size-5 -translate-y-1/2 items-center justify-center text-placeholder"
          >
            {rightIcon}
          </button>
        ) : (
          <span className="absolute right-4 top-1/2 flex size-5 -translate-y-1/2 items-center justify-center text-placeholder">
            {rightIcon}
          </span>
        )
      ) : null}
    </div>
  );
}
