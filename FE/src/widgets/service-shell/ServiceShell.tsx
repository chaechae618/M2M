"use client";

import { Suspense, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { ServiceBottomNavigation } from "@/widgets/service-bottom-navigation/ServiceBottomNavigation";
import { ServiceSidebar, ServiceSidebarProvider } from "@/widgets/service-sidebar/ServiceSidebar";

export function ServiceShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isFullWidthServicePage = pathname.startsWith("/knowledge") || pathname.startsWith("/my");

  if (isFullWidthServicePage) {
    return (
      <div className="flex min-h-dvh w-full flex-col bg-white">
        <div className="min-h-0 flex-1 pb-[104px]">{children}</div>
        <ServiceBottomNavigation
          hideOnChat
          className="!fixed !bottom-6 !left-1/2 !z-30 !m-0 !-translate-x-1/2"
        />
      </div>
    );
  }

  return (
    <ServiceSidebarProvider>
      <div className="flex h-dvh min-h-[720px] w-full bg-[#f9f9f9] py-2 pr-2">
        <Suspense fallback={<aside className="h-full w-[68px] shrink-0" />}>
          <ServiceSidebar />
        </Suspense>
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="min-h-0 flex-1">{children}</div>
          <ServiceBottomNavigation hideOnChat />
        </div>
      </div>
    </ServiceSidebarProvider>
  );
}
