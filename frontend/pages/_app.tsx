import "@/styles/globals.css";
import type { AppProps } from "next/app";
import Link from "next/link";
import { useRouter } from "next/router";

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const isDashboard = router.pathname.startsWith("/dashboard");

  return (
    <>
      <header className="bg-purple-700 text-white p-4 flex justify-between items-center">
        <div className="font-bold text-xl">
          <Link href="/">ResumeParse</Link>
        </div>
        <nav className="space-x-4">
          <Link href="/">Home</Link>
          <Link href="/pricing">Pricing</Link>
          <Link href="/docs">Docs</Link>
          {isDashboard && (
            <>
              <Link href="/dashboard">Dashboard</Link>
              <Link href="/dashboard/account">Account</Link>
              <Link href="/dashboard/logout">Logout</Link>
            </>
          )}
        </nav>
      </header>

      <main className="p-6">
        <Component {...pageProps} />
      </main>

      <footer className="text-center p-4 text-sm text-gray-500 border-t mt-6">
        &copy; {new Date().getFullYear()} ResumeParse. All rights reserved.
      </footer>
    </>
  );
}
