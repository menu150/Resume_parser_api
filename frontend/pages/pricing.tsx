import Head from "next/head";

export default function PricingPage() {
  return (
    <>
      <Head>
        <title>Pricing – ResumeParse</title>
      </Head>
      <main className="p-10">
        <h1 className="text-4xl font-bold text-purple-700 mb-6">Pricing</h1>
        <div className="space-y-4">
          <div className="p-6 border rounded shadow">
            <h2 className="text-xl font-semibold">Free Tier</h2>
            <p>✅ 50 resumes/month</p>
            <p>✅ API access</p>
            <p>💸 $0/month</p>
          </div>
          <div className="p-6 border rounded shadow">
            <h2 className="text-xl font-semibold">Pro Tier</h2>
            <p>✅ 2,000 resumes/month</p>
            <p>✅ Priority support</p>
            <p>💸 $19/month</p>
          </div>
        </div>
      </main>
    </>
  );
}
