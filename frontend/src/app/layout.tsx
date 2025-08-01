import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ResumeParse API",
  description: "AI-powered resume parsing. Instantly extract structured data from resumes.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} bg-white text-gray-900 font-sans flex flex-col min-h-screen`}>
        <header className="w-full bg-purple-700 text-white p-4 flex justify-between items-center">
          <div className="text-2xl font-bold">ResumeParse</div>
          <nav className="space-x-6">
            <a href="/" className="hover:text-gray-200">Home</a>
            <a href="/pricing" className="hover:text-gray-200">Pricing</a>
            <a href="/docs" className="hover:text-gray-200">Docs</a>
          </nav>
        </header>

        <main className="flex-1 p-6">{children}</main>

        <footer className="w-full bg-gray-100 text-gray-700 p-4 text-center">
          &copy; {new Date().getFullYear()} ResumeParse. All rights reserved.
        </footer>
      </body>
    </html>
  );
}
