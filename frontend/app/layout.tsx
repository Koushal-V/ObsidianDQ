import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ObsidianDQ - Data Observability & Healing Platform",
  description: "Deterministic & Agentic Data Quality, Observability, and Self-Healing Engine",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#FFF4EB] text-[#3D1534] antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
