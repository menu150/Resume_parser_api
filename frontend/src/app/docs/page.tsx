export default function Docs() {
  return (
    <main className="p-8">
      <h1 className="text-3xl font-bold mb-4">API Documentation</h1>
      <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto">
        {`
POST /api/parse
Authorization: Bearer <API_KEY>
Content-Type: multipart/form-data
        `}
      </pre>
    </main>
  );
}
