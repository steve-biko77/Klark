'use client'

import { Suspense, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { login } from '@/lib/auth'

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  )
}

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const expired = searchParams.get('expired') === '1'

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const data = await login(username, password)
      router.push(
        `/verify-otp?user_id=${data.user_id}&email=${encodeURIComponent(data.email)}&username=${encodeURIComponent(data.username)}`
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de connexion')
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md p-8 bg-white rounded-2xl shadow-sm border border-gray-100">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Connexion</h1>
        <p className="text-gray-500 mb-8">Content de te revoir sur Klark</p>

        {expired && (
          <p className="mb-4 text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
            Ta session a expiré, merci de te reconnecter.
          </p>
        )}

        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">
              Nom d&apos;utilisateur
            </label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="ton_pseudo"
              required
              className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Mot de passe</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {loading ? 'Vérification...' : 'Se connecter'}
          </button>
        </form>

        <div className="mt-6 flex flex-col gap-3 text-center text-sm text-gray-500">
          <Link href="/forgot-password" className="text-indigo-600 hover:underline">
            Mot de passe oublié ?
          </Link>
          <span>
            Pas encore de compte ?{' '}
            <Link href="/register" className="text-indigo-600 hover:underline">
              S&apos;inscrire
            </Link>
          </span>
        </div>
      </div>
    </div>
  )
}
