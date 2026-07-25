import { ServiceBottomNavigation } from "@/widgets/service-bottom-navigation/ServiceBottomNavigation";

export default function ServiceLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="min-h-screen bg-white">
      {children}
      <ServiceBottomNavigation hideOnChat />
    </div>
  );
}
