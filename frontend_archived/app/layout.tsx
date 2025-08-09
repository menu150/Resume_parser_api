// /frontend/app/layout.tsx
import "./globals.css";
import { ReactNode } from "react";

export const metadata = {
  title: "ResumeParse API",
  description: "AI-powered Resume Parsing. Simple. Fast. Powerful.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-white text-gray-900">
        <main className="min-h-screen flex flex-col items-center justify-center px-4">
          {children}
        </main>
      </body>
    </html>
  );
}
