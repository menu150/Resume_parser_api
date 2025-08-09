// frontend/app/page.tsx
export default function Home() {
  return (
    <main className="min-h-screen bg-white text-black px-6 py-24 lg:px-8">
      <div className="text-center max-w-3xl mx-auto">
        <h1 className="text-5xl font-bold tracking-tight text-purple-700">ResumeParse API</h1>
        <p className="mt-6 text-lg leading-8 text-gray-700">
          Instantly extract structured resume data using our blazing-fast API. No setup, no training required.
        </p>
        <div className="mt-10 flex items-center justify-center gap-x-6">
          <a
            href="/pricing"
            className="rounded-md bg-purple-700 px-6 py-3 text-md font-semibold text-white hover:bg-purple-800"
          >
            Get Started
          </a>
          <a
            href="/docs"
            className="text-md font-semibold leading-6 text-gray-900"
          >
            View Docs →
          </a>
        </div>
      </div>
    </main>
  );
}
