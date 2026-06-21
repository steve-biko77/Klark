'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { verifyOTP, resendOTP } from '@/lib/auth'

const OTP_TTL = 10 * 60 // 10 minutes en secondes

export default function VerifyOTPPage() {
  const router = useRouter()
  const params = useSearchParams()

  const userId = Number(params.get('user_id'))
  const email = params.get('email') ?? ''
  const username = params.get('username') ?? ''

  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [resending, setResending] = useState(false)
  const [resendSuccess, setResendSuccess] = useState(false)
  const [secondsLeft, setSecondsLeft] = useState(OTP_TTL)

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setSecondsLeft(s => {
        if (s <= 1) {
          clearInterval(intervalRef.current!)
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => clearInterval(intervalRef.current!)
  }, [])

  function formatTime(s: number) {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault()
    if (!userId) {
      setError('Session invalide, reconnectez-vous.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await verifyOTP(userId, code, username)
      router.push('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Code invalide')
      setLoading(false)
    }
  }

  async function handleResend() {
    setResending(true)
    setError('')
    setResendSuccess(false)
    try {
      await resendOTP(userId)
      setSecondsLeft(OTP_TTL)
      setResendSuccess(true)
      setCode('')
    } catch {
      setError('Impossible de renvoyer le code.')
    }
    setResending(false)
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md p-8 bg-white rounded-2xl shadow-sm border border-gray-100">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Vérification en deux étapes</h1>
        <p className="text-gray-500 mb-2">
          Un code à 6 chiffres a été envoyé à{' '}
          <span className="font-medium text-gray-700">{email}</span>
        </p>

        <div className={`text-sm font-medium mb-6 ${secondsLeft <= 60 ? 'text-red-500' : 'text-gray-400'}`}>
          {secondsLeft > 0 ? `Code valide encore ${formatTime(secondsLeft)}` : 'Code expiré — demandez-en un nouveau'}
        </div>

        <form onSubmit={handleVerify} className="flex flex-col gap-4">
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Code à 6 chiffres</label>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="123456"
              required
              autoFocus
              className="w-full border border-gray-200 rounded-lg px-4 py-3 text-center text-2xl tracking-widest font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}
          {resendSuccess && <p className="text-green-600 text-sm">Nouveau code envoyé !</p>}

          <button
            type="submit"
            disabled={loading || secondsLeft === 0 || code.length !== 6}
            className="bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {loading ? 'Vérification...' : 'Confirmer'}
          </button>
        </form>

        <button
          onClick={handleResend}
          disabled={resending}
          className="mt-4 w-full text-sm text-indigo-600 hover:underline disabled:opacity-50"
        >
          {resending ? 'Envoi en cours...' : 'Renvoyer le code'}
        </button>

        <p className="text-center text-sm text-gray-400 mt-6">
          <a href="/login" className="hover:underline">← Retour à la connexion</a>
        </p>
      </div>
    </div>
  )
}
