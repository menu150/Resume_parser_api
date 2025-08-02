import Head from "next/head";

export default function DocsPage() {
  return (
    <>
      <Head>
        <title>API Docs – ResumeParse</title>
      </Head>
      <main className="p-10">
        <h1 className="text-4xl font-bold text-purple-700 mb-6">API Documentation</h1>
        <p className="mb-4">POST your PDF resume to this endpoint:</p>
        <code className="block bg-gray-100 p-2 rounded">
          POST https://your-api-url.com/upload_resume<br/>
          Headers: {`{ "x-api-key": "your_api_key_here" }`}<br/>
          Body: form-data with file field named `resume`
        </code>

        <p className="mt-6">Response Example:</p>
        <pre className="bg-gray-800 text-white p-4 rounded text-sm overflow-x-auto">
{`{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "skills": ["Python", "SQL"],
  "experience": [...]
}`}
        </pre>
      </main>
    </>
  );
}
