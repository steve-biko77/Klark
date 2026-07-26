'use client'

import { Suspense, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export default function UnsubscribePage() {
  return (
    <Suspense fallback={null}>
      <UnsubscribeContent />
    </Suspense>
  )
}

function UnsubscribeContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')
  const isWeekly = searchParams.get('type') === 'weekly'
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>(token ? 'loading' : 'error')

  useEffect(() => {
    if (!token) return
    const path = isWeekly ? '/briefings/unsubscribe-weekly/' : '/briefings/unsubscribe/'
    fetch(`${BASE_URL}${path}?token=${encodeURIComponent(token)}`)
      .then(res => setStatus(res.ok ? 'success' : 'error'))
      .catch(() => setStatus('error'))
  }, [token, isWeekly])

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md p-8 bg-white rounded-2xl shadow-sm border border-gray-100 text-center">
        {status === 'loading' && <p className="text-gray-500">Traitement en cours...</p>}
        {status === 'success' && (
          <>
            <div className="text-4xl mb-4">✅</div>
            <h1 className="text-xl font-bold text-gray-900 mb-2">Désabonnement confirmé</h1>
            <p className="text-gray-500">
              {isWeekly
                ? 'Tu ne recevras plus le bilan hebdomadaire de Klark.'
                : 'Tu ne recevras plus le digest email matinal de Klark.'}
            </p>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="text-4xl mb-4">⚠️</div>
            <h1 className="text-xl font-bold text-gray-900 mb-2">Lien invalide ou expiré</h1>
            <p className="text-gray-500">Connecte-toi à Klark pour gérer tes préférences de notifications.</p>
          </>
        )}
      </div>
    </div>
  )
}
