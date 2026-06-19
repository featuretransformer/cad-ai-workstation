import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI-Native CAD Workstation",
  description: "Multi-agent AI system for parametric CAD design and manufacturing — natural language to manufacturable geometry",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
