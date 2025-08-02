import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";


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
      <body className={`${geistSans.variable} ${geistMono.variable} bg-white text-gray-900 min-h-screen flex flex-col`}>
        {/* Header/Navbar */}
        <header className="w-full bg-purple-700 text-white p-4 flex justify-between items-center shadow-md">
          <div className="text-2xl font-bold tracking-tight">ResumeParse</div>
          <nav className="space-x-6 text-lg">
            <Link href="/" className="hover:text-gray-200">Home</Link>
            <Link href="/pricing" className="hover:text-gray-200">Pricing</Link>
            <Link href="/docs" className="hover:text-gray-200">Docs</Link>
          </nav>
        </header>

        {/* Main content */}
        <main className="flex-1 p-6 max-w-6xl mx-auto w-full">
          {children}
        </main>

        {/* Footer */}
        <footer className="w-full bg-gray-100 text-gray-600 text-sm p-4 text-center border-t border-gray-200">
          &copy; {new Date().getFullYear()} ResumeParse. All rights reserved.
        </footer>
      </body>
    </html>
  );
}
