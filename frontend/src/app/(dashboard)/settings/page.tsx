'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getToken } from '@/lib/auth'
import { apiFetch } from '@/lib/api'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

type LinkedInStatus = {
  connected: boolean
  expires_at: string | null
}

function LinkedInIcon() {
  return (
    <div className="w-9 h-9 rounded-lg bg-[#0A66C2] flex items-center justify-center flex-shrink-0">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="white" aria-hidden>
        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
      </svg>
    </div>
  )
}

export default function SettingsPage() {
  const [linkedIn, setLinkedIn] = useState<LinkedInStatus>({ connected: false, expires_at: null })
  const [loadingStatus, setLoadingStatus] = useState(true)
  const [disconnecting, setDisconnecting] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [toastType, setToastType] = useState<'success' | 'error'>('success')

  async function loadStatus() {
    const token = getToken()
    try {
      const data = await apiFetch('/posts/linkedin/status/', token!)
      setLinkedIn(data)
    } catch {
      setLinkedIn({ connected: false, expires_at: null })
    }
    setLoadingStatus(false)
  }

  function showToast(message: string, type: 'success' | 'error' = 'success') {
    setToast(message)
    setToastType(type)
  }

  useEffect(() => {
    loadStatus()

    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      const linkedinParam = params.get('linkedin')
      if (linkedinParam === 'connected') {
        showToast('LinkedIn connecté ✓')
        window.history.replaceState({}, '', '/settings')
      } else if (linkedinParam === 'error') {
        showToast('Erreur lors de la connexion LinkedIn', 'error')
        window.history.replaceState({}, '', '/settings')
      }
    }
  }, [])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(t)
  }, [toast])

  function handleConnectLinkedIn() {
    const token = getToken()
    window.location.href = `${BASE_URL}/posts/linkedin/auth/?token=${token}`
  }

  async function handleDisconnect() {
    if (!confirm('Déconnecter LinkedIn ?')) return
    setDisconnecting(true)
    const token = getToken()
    try {
      await apiFetch('/posts/linkedin/disconnect/', token!, { method: 'DELETE' })
      setLinkedIn({ connected: false, expires_at: null })
      showToast('LinkedIn déconnecté')
    } catch {
      showToast('Erreur lors de la déconnexion', 'error')
    }
    setDisconnecting(false)
  }

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-6 right-6 px-5 py-3 rounded-xl shadow-lg text-sm font-medium z-50 border ${
            toastType === 'error'
              ? 'bg-red-50 text-red-700 border-red-200'
              : 'bg-green-50 text-green-700 border-green-200'
          }`}
        >
          {toast}
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Paramètres</h1>
        <p className="text-gray-500 mt-1">Gérez vos connexions et préférences éditoriales</p>
      </div>

      {/* Comptes connectés */}
      <div className="bg-white rounded-xl border border-gray-100 p-6 flex flex-col gap-5">
        <h2 className="text-base font-semibold text-gray-900">Comptes connectés</h2>

        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <LinkedInIcon />
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900">LinkedIn</p>
              {linkedIn.connected && linkedIn.expires_at && (
                <p className="text-xs text-gray-400">
                  Expire le{' '}
                  {new Date(linkedIn.expires_at).toLocaleDateString('fr-FR', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric',
                  })}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {loadingStatus ? (
              <span className="text-xs text-gray-400">Chargement...</span>
            ) : linkedIn.connected ? (
              <>
                <span className="flex items-center gap-1.5 text-xs font-medium text-green-600 bg-green-50 border border-green-200 px-3 py-1 rounded-full">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
                  Connecté
                </span>
                <button
                  onClick={handleDisconnect}
                  disabled={disconnecting}
                  className="text-xs text-red-500 bg-red-50 border border-red-200 px-3 py-1 rounded-full hover:bg-red-100 transition disabled:opacity-50"
                >
                  {disconnecting ? 'Déconnexion...' : 'Déconnecter'}
                </button>
              </>
            ) : (
              <button
                onClick={handleConnectLinkedIn}
                className="flex items-center gap-2 bg-[#0A66C2] text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-[#004182] transition"
              >
                Connecter LinkedIn
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Profil éditorial */}
      <div className="bg-white rounded-xl border border-gray-100 p-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Profil éditorial</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Persona, secteur, ton et style — utilisés pour générer vos posts et évaluer vos articles
          </p>
        </div>
        <Link
          href="/settings/profile"
          className="shrink-0 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
        >
          Configurer →
        </Link>
      </div>

      {/* Alertes mots-clés */}
      <div className="bg-white rounded-xl border border-gray-100 p-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Alertes mots-clés</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Soyez notifié dès qu'un article contient un mot-clé important pour vous
          </p>
        </div>
        <Link
          href="/settings/alerts"
          className="shrink-0 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
        >
          Configurer →
        </Link>
      </div>
    </div>
  )
}
