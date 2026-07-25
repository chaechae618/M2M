import { ServiceShell } from "@/widgets/service-shell/ServiceShell";

export default function ServiceLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <ServiceShell>{children}</ServiceShell>;
}
