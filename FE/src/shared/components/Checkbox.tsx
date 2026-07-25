import Image from "next/image";
import type { InputHTMLAttributes } from "react";
import { cn } from "@/shared/lib/cn";

type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label: string;
};

export function Checkbox({ className, label, ...props }: CheckboxProps) {
  return (
    <label className="inline-flex items-center gap-1.5 text-[14px] font-medium leading-[1.4] text-brand-muted">
      <input
        type="checkbox"
        className={cn("figma-checkbox-input sr-only", className)}
        {...props}
      />
      <span className="figma-checkbox-box relative size-5 shrink-0">
        <span className="figma-checkbox-empty absolute inset-[8.33%] rounded-[3px] border border-line-soft" />
        <Image
          src="/figma-assets/check-solid.svg"
          alt=""
          width={17}
          height={17}
          className="figma-checkbox-checked absolute inset-[8.33%] hidden size-[83.34%]"
          draggable={false}
        />
      </span>
      <span>{label}</span>
    </label>
  );
}
