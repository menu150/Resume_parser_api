import "@/styles/globals.css";
import Link from "next/link";

export default function App({ Component, pageProps }) {
  return (
    <>
      <header className="bg-purple-700 text-white p-4 flex justify-between">
        <div className="font-bold text-xl">ResumeParse</div>
        <nav className="space-x-4">
          <Link href="/">Home</Link>
          <Link href="/pricing">Pricing</Link>
          <Link href="/docs">Docs</Link>
        </nav>
      </header>
      <Component {...pageProps} />
      <footer className="text-center p-4 text-sm text-gray-500 border-t mt-6">
        &copy; {new Date().getFullYear()} ResumeParse. All rights reserved.
      </footer>
    </>
  );
}
