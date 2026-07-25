import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mento to Mentee",
  description: "AI가 진로 고민을 구체적인 질문과 답변으로 바꾸는 멘토링 서비스",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
