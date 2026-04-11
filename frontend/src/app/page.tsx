import Link from 'next/link'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6">
      <h1 className="text-5xl font-bold text-indigo-600">Klark</h1>
      <p className="text-gray-500 text-lg">Automatise ta présence numérique</p>
      <Link
        href="/login"
        className="bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 transition"
      >
        Commencer
      </Link>
    </main>
  )
}