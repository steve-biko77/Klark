'use client'

import { useEffect, useState } from 'react'
import { getToken } from '@/lib/auth'
import { apiFetch } from '@/lib/api'

const HOUR_OPTIONS = [5, 6, 7, 8, 9, 10]

export default function NotificationsSettingsPage() {
  const [emailDigest, setEmailDigest] = useState(true)
  const [digestHour, setDigestHour] = useState(7)
  const [weeklyDigest, setWeeklyDigest] = useState(true)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState('')
  const [sendingWeekly, setSendingWeekly] = useState(false)
  const [sendWeeklyResult, setSendWeeklyResult] = useState('')

  useEffect(() => {
    const token = getToken()
    apiFetch('/profile/', token)
      .then(profile => {
        setEmailDigest(profile.email_digest)
        setDigestHour(profile.digest_hour)
        setWeeklyDigest(profile.weekly_digest)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function handleSave() {
    setSaving(true)
    const token = getToken()
    try {
      await apiFetch('/profile/', token, {
        method: 'PATCH',
        body: JSON.stringify({ email_digest: emailDigest, digest_hour: digestHour, weekly_digest: weeklyDigest }),
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      alert('Erreur lors de la sauvegarde')
    }
    setSaving(false)
  }

  async function handleSendNow() {
    setSending(true)
    setSendResult('')
    const token = getToken()
    try {
      const response = await apiFetch('/briefings/send-digest/', token, { method: 'POST' })
      setSendResult(response.sent ? 'Digest envoyé ✓ (regarde ta boîte mail / la console du serveur en dev)' : 'Digest désactivé — active-le puis réessaie.')
    } catch {
      setSendResult('Erreur lors de l\'envoi.')
    }
    setSending(false)
  }

  async function handleSendWeeklyNow() {
    setSendingWeekly(true)
    setSendWeeklyResult('')
    const token = getToken()
    try {
      const response = await apiFetch('/briefings/send-weekly-digest/', token, { method: 'POST' })
      setSendWeeklyResult(response.sent ? 'Bilan hebdo envoyé ✓' : 'Digest hebdo désactivé — active-le puis réessaie.')
    } catch {
      setSendWeeklyResult('Erreur lors de l\'envoi.')
    }
    setSendingWeekly(false)
  }

  if (loading) {
    return <p className="text-gray-400 text-sm">Chargement...</p>
  }

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Notifications par email</h1>
        <p className="text-gray-500 mt-1">
          Reçois chaque matin un résumé personnalisé de tes meilleurs signaux et articles.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6 flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-900">Digest email matinal</p>
            <p className="text-xs text-gray-400 mt-0.5">Envoyé par email tous les jours</p>
          </div>
          <button
            onClick={() => setEmailDigest(v => !v)}
            className={`w-11 h-6 rounded-full transition relative ${emailDigest ? 'bg-indigo-600' : 'bg-gray-200'}`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                emailDigest ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {emailDigest && (
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">Heure de réception</label>
            <select
              value={digestHour}
              onChange={e => setDigestHour(Number(e.target.value))}
              className="border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {HOUR_OPTIONS.map(h => (
                <option key={h} value={h}>{h}h00</option>
              ))}
            </select>
          </div>
        )}

        <button
          onClick={handleSave}
          disabled={saving}
          className="self-start bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
        >
          {saved ? 'Enregistré ✓' : saving ? 'Sauvegarde...' : 'Enregistrer'}
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6 flex flex-col gap-3">
        <p className="text-sm font-medium text-gray-900">Tester maintenant</p>
        <p className="text-xs text-gray-400">
          Envoie le digest immédiatement (utile pour vérifier le rendu sans attendre le lendemain matin).
        </p>
        <button
          onClick={handleSendNow}
          disabled={sending}
          className="self-start border border-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition disabled:opacity-50"
        >
          {sending ? 'Envoi...' : 'Envoyer le digest maintenant'}
        </button>
        {sendResult && <p className="text-xs text-gray-500">{sendResult}</p>}
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6 flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-900">Bilan hebdomadaire</p>
            <p className="text-xs text-gray-400 mt-0.5">
              Chaque lundi : posts publiés, engagement, série et score d&apos;influence de la semaine
            </p>
          </div>
          <button
            onClick={() => setWeeklyDigest(v => !v)}
            className={`w-11 h-6 rounded-full transition relative ${weeklyDigest ? 'bg-indigo-600' : 'bg-gray-200'}`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                weeklyDigest ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        <p className="text-xs text-gray-400 -mt-2">
          Le bouton &quot;Enregistrer&quot; de la section digest matinal ci-dessus sauvegarde aussi ce réglage.
        </p>

        <div className="border-t border-gray-100 pt-4 flex flex-col gap-2">
          <button
            onClick={handleSendWeeklyNow}
            disabled={sendingWeekly}
            className="self-start border border-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition disabled:opacity-50"
          >
            {sendingWeekly ? 'Envoi...' : 'Envoyer le bilan hebdo maintenant'}
          </button>
          {sendWeeklyResult && <p className="text-xs text-gray-500">{sendWeeklyResult}</p>}
        </div>
      </div>
    </div>
  )
}
