// frontend/pages/_app.tsx
import type { AppProps } from "next/app";
import "../src/app/globals.css";    // ← re-use your globals.css with @tailwind directives

export default function MyApp({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />;
}
