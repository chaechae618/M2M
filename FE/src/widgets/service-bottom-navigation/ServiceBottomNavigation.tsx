"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { routes } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/cn";

const items = [
  { href: routes.chat, icon: "/figma-assets/chat/nav-home.svg", label: "홈" },
  { href: routes.knowledge, icon: "/figma-assets/qna-nav-qna.svg", label: "Q&A" },
  { href: routes.my, icon: "/figma-assets/qna-nav-profile.svg", label: "마이" },
];

type ServiceBottomNavigationProps = {
  className?: string;
  hideOnChat?: boolean;
};

export function ServiceBottomNavigation({ className, hideOnChat = false }: ServiceBottomNavigationProps) {
  const pathname = usePathname();

  if (hideOnChat && (pathname === routes.chat || pathname.startsWith(`${routes.chat}/`))) {
    return null;
  }

  return (
    <nav
      className={cn(
        "mx-auto mb-6 mt-3 w-fit rounded-[40px] bg-[rgba(247,247,247,0.7)] px-3 py-2 shadow-[0_6px_20px_rgba(68,74,83,0.12)] backdrop-blur",
        className,
      )}
    >
      <div className="flex items-center gap-2">
        {items.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex h-10 items-center justify-center rounded-[40px] px-3",
                active ? "gap-1.5 bg-accent-orange text-white" : "text-[#242424]",
              )}
              aria-label={item.label}
            >
              {active ? (
                <span className="text-[16px] font-medium leading-[1.7]">{item.label}</span>
              ) : null}
              <Image src={item.icon} alt="" width={24} height={24} className="size-6" draggable={false} />
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
