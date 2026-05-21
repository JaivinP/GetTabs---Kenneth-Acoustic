import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GetTabs",
  description: "Extract guitar tabs from YouTube tutorials into a printable PDF",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
