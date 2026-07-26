'use client'

import { useEffect, useState } from 'react'
import { getToken } from '@/lib/auth'
import { apiFetch } from '@/lib/api'

type Alert = {
  id: number
  keyword: string
  is_active: boolean
  created_at: string
}

const MAX_ACTIVE_ALERTS = 10

export default function AlertsSettingsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [keyword, setKeyword] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')

  const activeCount = alerts.filter(a => a.is_active).length

  async function loadAlerts() {
    const token = getToken()
    try {
      const data = await apiFetch('/alerts/', token)
      setAlerts(data)
    } catch {
      setAlerts([])
    }
    setLoading(false)
  }

  useEffect(() => { loadAlerts() }, [])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!keyword.trim()) return
    setAdding(true)
    setError('')
    const token = getToken()
    try {
      const created = await apiFetch('/alerts/', token, {
        method: 'POST',
        body: JSON.stringify({ keyword: keyword.trim() }),
      })
      setAlerts(prev => [created, ...prev])
      setKeyword('')
    } catch {
      setError(`Impossible d'ajouter l'alerte (maximum ${MAX_ACTIVE_ALERTS} alertes actives).`)
    }
    setAdding(false)
  }

  async function handleToggle(alert: Alert) {
    const token = getToken()
    try {
      const updated = await apiFetch(`/alerts/${alert.id}/`, token, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !alert.is_active }),
      })
      setAlerts(prev => prev.map(a => (a.id === alert.id ? updated : a)))
    } catch {
      setError(`Impossible d'activer plus de ${MAX_ACTIVE_ALERTS} alertes.`)
    }
  }

  async function handleDelete(alert: Alert) {
    const token = getToken()
    try {
      await apiFetch(`/alerts/${alert.id}/`, token, { method: 'DELETE' })
      setAlerts(prev => prev.filter(a => a.id !== alert.id))
    } catch {
      setError("Erreur lors de la suppression de l'alerte.")
    }
  }

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Alertes mots-clés</h1>
        <p className="text-gray-500 mt-1">
          Sois notifié dès qu&apos;un article contient un de tes mots-clés. {activeCount}/{MAX_ACTIVE_ALERTS} alertes actives.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6 flex flex-col gap-5">
        <form onSubmit={handleAdd} className="flex gap-2">
          <input
            type="text"
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            placeholder="Ex : Fed rate, BTC crash, inflation..."
            className="flex-1 border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={adding || !keyword.trim() || activeCount >= MAX_ACTIVE_ALERTS}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
          >
            Ajouter
          </button>
        </form>

        {error && <p className="text-sm text-red-500">{error}</p>}

        {loading ? (
          <p className="text-gray-400 text-sm">Chargement...</p>
        ) : alerts.length === 0 ? (
          <p className="text-gray-400 text-sm">Aucune alerte configurée.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {alerts.map(alert => (
              <div
                key={alert.id}
                className="flex items-center justify-between gap-3 border border-gray-100 rounded-lg px-4 py-2.5"
              >
                <span className={`text-sm font-medium ${alert.is_active ? 'text-gray-900' : 'text-gray-400'}`}>
                  {alert.keyword}
                </span>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleToggle(alert)}
                    className={`text-xs px-3 py-1 rounded-full font-medium border transition ${
                      alert.is_active
                        ? 'bg-green-50 text-green-700 border-green-200 hover:bg-green-100'
                        : 'bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100'
                    }`}
                  >
                    {alert.is_active ? 'Active' : 'Désactivée'}
                  </button>
                  <button
                    onClick={() => handleDelete(alert)}
                    className="text-xs text-red-500 bg-red-50 border border-red-200 px-3 py-1 rounded-full hover:bg-red-100 transition"
                  >
                    Supprimer
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
