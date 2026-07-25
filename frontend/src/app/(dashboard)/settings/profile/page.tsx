'use client'

import { useEffect, useState } from 'react'
import { getToken } from '@/lib/auth'
import { apiFetch } from '@/lib/api'

type Persona = 'TRADER' | 'CREATEUR' | 'JOURNALISTE' | 'POLITICIEN' | 'PASSIONNE'
type Tone = 'EXPERT' | 'ACCESSIBLE' | 'DIRECT'

type Profile = {
  persona: Persona
  style_prompt: string
  sector: string
  tone: Tone
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
    </div>
  )
}
