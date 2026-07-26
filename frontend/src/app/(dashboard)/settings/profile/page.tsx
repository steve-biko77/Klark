'use client'

import { useEffect, useState } from 'react'
import { getToken } from '@/lib/auth'
import { apiFetch } from '@/lib/api'

type Persona = 'TRADER' | 'CREATEUR' | 'JOURNALISTE' | 'POLITICIEN' | 'PASSIONNE'
type Tone = 'EXPERT' | 'ACCESSIBLE' | 'DIRECT'

type StyleHistoryEntry = { date: string; learned_text: string; posts_analyzed: number }

type Profile = {
  persona: Persona
  style_prompt: string
  sector: string
  tone: Tone
  style_history?: StyleHistoryEntry[]
}

const PERSONA_OPTIONS: { value: Persona; label: string; description: string }[] = [
  { value: 'TRADER', label: 'Trader', description: 'Signaux marché, analyse rapide, ton analytique.' },
  { value: 'CREATEUR', label: 'Créateur', description: 'Contenu régulier pour construire une audience.' },
  { value: 'JOURNALISTE', label: 'Journaliste', description: 'Factuel, sourcé, ton neutre.' },
  { value: 'POLITICIEN', label: 'Politicien', description: 'Prises de position, communication publique.' },
  { value: 'PASSIONNE', label: 'Passionné', description: 'Partage de passion sans objectif professionnel.' },
]

const TONE_OPTIONS: { value: Tone; label: string; example: string }[] = [
  { value: 'EXPERT', label: 'Expert', example: '"Les données montrent une corrélation claire entre..."' },
  { value: 'ACCESSIBLE', label: 'Accessible', example: '"En clair, ça veut dire que..."' },
  { value: 'DIRECT', label: 'Direct', example: '"Voici ce qu\'il faut retenir : ..."' },
]

const DEFAULT_PROFILE: Profile = { persona: 'CREATEUR', style_prompt: '', sector: '', tone: 'EXPERT' }

export default function ProfileSettingsPage() {
  const [profile, setProfile] = useState<Profile>(DEFAULT_PROFILE)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [showLearning, setShowLearning] = useState(false)
  const [learning, setLearning] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [learnMessage, setLearnMessage] = useState('')

  useEffect(() => {
    const token = getToken()
    apiFetch('/profile/', token)
      .then(data => setProfile(data))
      .catch(() => setProfile(DEFAULT_PROFILE))
      .finally(() => setLoading(false))
  }, [])

  async function handleSave() {
    setSaving(true)
    const token = getToken()
    try {
      const updated = await apiFetch('/profile/', token, {
        method: 'PATCH',
        body: JSON.stringify(profile),
      })
      setProfile(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      alert('Erreur lors de la sauvegarde du profil')
    }
    setSaving(false)
  }

  async function handleLearnStyle() {
    setLearning(true)
    setLearnMessage('')
    const token = getToken()
    try {
      const result = await apiFetch('/profile/learn-style/', token, { method: 'POST' })
      if (result.updated) {
        setProfile(p => ({ ...p, style_prompt: result.style_prompt, style_history: result.style_history }))
        setLearnMessage('Mémoire mise à jour ✓')
      } else {
        setLearnMessage(result.message ?? 'Pas assez de posts publiés pour le moment.')
      }
    } catch {
      setLearnMessage('Erreur lors de l\'apprentissage')
    }
    setLearning(false)
    setTimeout(() => setLearnMessage(''), 4000)
  }

  async function handleResetStyle() {
    if (!confirm('Réinitialiser le style à la valeur saisie manuellement ?')) return
    setResetting(true)
    const token = getToken()
    try {
      const updated = await apiFetch('/profile/reset-style/', token, { method: 'POST' })
      setProfile(updated)
    } catch {
      alert('Erreur lors de la réinitialisation')
    }
    setResetting(false)
  }

  if (loading) {
    return <p className="text-gray-400 text-sm">Chargement...</p>
  }

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profil éditorial</h1>
        <p className="text-gray-500 mt-1">
          Klark utilise ce profil pour générer vos posts et évaluer la pertinence des articles.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6 flex flex-col gap-6">
        <div>
          <label className="text-sm font-medium text-gray-700 mb-2 block">Persona</label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {PERSONA_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setProfile(p => ({ ...p, persona: opt.value }))}
                className={`text-left p-3 rounded-lg border transition ${
                  profile.persona === opt.value
                    ? 'border-indigo-600 bg-indigo-50'
                    : 'border-gray-200 hover:border-indigo-300'
                }`}
              >
                <p className="text-sm font-medium text-gray-900">{opt.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{opt.description}</p>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700 mb-2 block">Secteur d&apos;activité</label>
          <input
            type="text"
            value={profile.sector}
            onChange={e => setProfile(p => ({ ...p, sector: e.target.value }))}
            placeholder="Ex : Finance et marchés, Tech & IA, Sport..."
            className="w-full border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700 mb-2 block">Ton éditorial</label>
          <div className="flex flex-col gap-2">
            {TONE_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setProfile(p => ({ ...p, tone: opt.value }))}
                className={`text-left p-3 rounded-lg border transition ${
                  profile.tone === opt.value
                    ? 'border-indigo-600 bg-indigo-50'
                    : 'border-gray-200 hover:border-indigo-300'
                }`}
              >
                <p className="text-sm font-medium text-gray-900">{opt.label}</p>
                <p className="text-xs text-gray-500 mt-0.5 italic">{opt.example}</p>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700 mb-2 block">Style éditorial</label>
          <textarea
            value={profile.style_prompt}
            onChange={e => setProfile(p => ({ ...p, style_prompt: e.target.value }))}
            rows={3}
            placeholder="Ex : J'écris des posts courts et percutants, je commence toujours par une question provoc."
            className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          />
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="self-start bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
        >
          {saved ? 'Enregistré ✓' : saving ? 'Sauvegarde...' : 'Enregistrer'}
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Mémoire de style</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Mémoire apprise : {profile.style_history?.length
                ? `${profile.style_history[profile.style_history.length - 1].posts_analyzed} posts analysés`
                : 'aucune donnée pour le moment'}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleLearnStyle}
            disabled={learning}
            className="text-xs border border-gray-200 text-gray-700 px-3 py-1.5 rounded-full hover:bg-gray-50 transition disabled:opacity-50"
          >
            {learning ? 'Analyse...' : 'Analyser mes posts performants'}
          </button>
          {!!profile.style_history?.length && (
            <button
              onClick={() => setShowLearning(v => !v)}
              className="text-xs border border-gray-200 text-gray-700 px-3 py-1.5 rounded-full hover:bg-gray-50 transition"
            >
              {showLearning ? 'Masquer l\'apprentissage' : 'Voir l\'apprentissage'}
            </button>
          )}
          <button
            onClick={handleResetStyle}
            disabled={resetting}
            className="text-xs border border-red-200 text-red-600 px-3 py-1.5 rounded-full hover:bg-red-50 transition disabled:opacity-50"
          >
            Réinitialiser
          </button>
        </div>

        {learnMessage && <p className="text-xs text-gray-500">{learnMessage}</p>}

        {showLearning && !!profile.style_history?.length && (
          <div className="flex flex-col gap-2 mt-1">
            {[...profile.style_history].reverse().map((entry, i) => (
              <div key={i} className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-400 mb-1">
                  {new Date(entry.date).toLocaleDateString('fr-FR')} · {entry.posts_analyzed} posts analysés
                </p>
                <p className="text-sm text-gray-700">{entry.learned_text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
