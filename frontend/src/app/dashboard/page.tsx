// src/app/dashboard/page.tsx

export default function Dashboard() {
  return (
    <section className="space-y-8">
      {/* Page title */}
      <h1 className="text-4xl font-extrabold text-purple-700">
        ResumeParse Dashboard
      </h1>

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard title="Uploads Today" value="14" />
        <StatCard title="Active API Keys" value="3" />
        <StatCard title="Quota Remaining" value="86 / 100" />
      </div>
    </section>
  );
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-2xl shadow p-6">
      <p className="text-sm text-gray-500">{title}</p>
      <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
    </div>
  );
}
