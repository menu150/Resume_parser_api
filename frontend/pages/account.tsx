import Head from "next/head";

export default function AccountPage() {
  return (
    <>
      <Head>
        <title>My Account – ResumeParse</title>
      </Head>
      <div className="max-w-2xl mx-auto p-6 space-y-6">
        <h1 className="text-3xl font-bold text-purple-700">Account Settings</h1>

        <section className="bg-white shadow p-4 rounded border">
          <h2 className="text-xl font-semibold mb-2">API Key</h2>
          <div className="flex justify-between items-center">
            <code className="bg-gray-100 px-3 py-1 rounded text-sm">sk_live_abcd1234xyz...</code>
            <button className="ml-2 px-3 py-1 text-sm bg-purple-600 text-white rounded hover:bg-purple-700">
              Regenerate
            </button>
          </div>
        </section>

        <section className="bg-white shadow p-4 rounded border">
          <h2 className="text-xl font-semibold mb-2">Usage</h2>
          <p><strong>Resumes parsed:</strong> 114 / 2000</p>
          <div className="w-full bg-gray-200 h-2 rounded mt-2">
            <div className="bg-purple-600 h-2 rounded" style={{ width: "5.7%" }}></div>
          </div>
        </section>

        <section className="bg-white shadow p-4 rounded border">
          <h2 className="text-xl font-semibold mb-2">Subscription</h2>
          <p>You are on the <strong>Pro Plan</strong>.</p>
          <button className="mt-2 px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-900">
            Manage Billing
          </button>
        </section>
      </div>
    </>
  );
}
