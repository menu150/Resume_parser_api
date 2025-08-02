// frontend/pages/index.tsx
export default function Home() {
  return (
    <section className="min-h-screen p-6 bg-gray-50">
      <h1 className="text-4xl font-extrabold text-purple-700 mb-8">
        ResumeParse Dashboard
      </h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Uploads Today" value="14" />
        <Card title="Active API Keys" value="3" />
        <Card title="Quota Remaining" value="86 / 100" />
      </div>
    </section>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-2xl shadow p-6">
      <p className="text-sm text-gray-500">{title}</p>
      <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
    </div>
  );
}
