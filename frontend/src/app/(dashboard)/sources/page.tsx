'use client'

import { useEffect, useState } from 'react'
import { getToken } from '@/lib/auth'
import { apiFetch } from '@/lib/api'

type Source = {
  id: string
  url: string
  name: string
  status: string
  last_crawled: string | null
  articles_count: number
  created_at: string
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'En attente',
  active: 'Active',
  error: 'Erreur',
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-500',
  active: 'bg-green-100 text-green-700',
  error: 'bg-red-100 text-red-700',
}

function relativeTime(dateStr: string | null): string {
  if (!dateStr) return 'Jamais'
  const diffMs = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(diffMs / 60000)
  if (minutes < 1) return "À l'instant"
  if (minutes < 60) return `Il y a ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `Il y a ${hours}h`
  const days = Math.floor(hours / 24)
  return `Il y a ${days}j`
}

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([])
  const [url, setUrl] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [candidates, setCandidates] = useState<string[]>([])

  async function loadSources() {
    const token = getToken()
    const data = await apiFetch('/sources/', token)
    setSources(data)
  }

  async function createSource(finalUrl: string) {
    const token = getToken()
    await apiFetch('/sources/', token, {
      method: 'POST',
      body: JSON.stringify({ url: finalUrl, name }),
    })
    setUrl('')
    setName('')
    setCandidates([])
    await loadSources()
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setCandidates([])
    try {
      const token = getToken()
      const result = await apiFetch('/sources/', token, {
        method: 'POST',
        body: JSON.stringify({ url, name }),
      })
      if (result.candidates) {
        setCandidates(result.candidates)
      } else {
        setUrl('')
        setName('')
        await loadSources()
      }
    } catch {
      setError("Aucun flux RSS détecté sur cette URL")
    }
    setLoading(false)
  }

  async function handlePickCandidate(candidateUrl: string) {
    setLoading(true)
    try {
      await createSource(candidateUrl)
    } catch {
      setError("Erreur lors de l'ajout de la source")
    }
    setLoading(false)
  }

  async function handleScrape(sourceId: string) {
    const token = getToken()
    try {
      const result = await apiFetch(`/sources/${sourceId}/scrape/`, token, { method: 'POST' })
      alert(`Scraping terminé — ${result.articles_added} article${result.articles_added > 1 ? 's' : ''} ajouté${result.articles_added > 1 ? 's' : ''}`)
      await loadSources()
    } catch {
      alert('Erreur lors du scraping')
    }
  }

  async function handleDelete(sourceId: string) {
    if (!confirm('Supprimer cette source et tous ses articles ?')) return
    const token = getToken()
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/sources/${sourceId}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      setSources(prev => prev.filter(s => s.id !== sourceId))
    } catch {
      alert('Erreur lors de la suppression')
    }
  }

  useEffect(() => { loadSources() }, [])

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sources</h1>
        <p className="text-gray-500 mt-1">
          Ajoute un flux RSS ou l&apos;URL d&apos;un site — Klark détecte le flux automatiquement
        </p>
      </div>

      <form onSubmit={handleAdd} className="bg-white rounded-xl p-6 border border-gray-100 flex flex-col gap-4">
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="text-sm font-medium text-gray-700 mb-1 block">Nom</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Ex: Le Monde Tech"
              className="w-full border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="flex-1">
            <label className="text-sm font-medium text-gray-700 mb-1 block">URL du site ou du flux RSS</label>
            <input
              type="url"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://exemple.com"
              required
              className="w-full border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        {candidates.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-gray-600">Plusieurs flux trouvés — choisis celui à ajouter :</p>
            {candidates.map(c => (
              <button
                key={c}
                type="button"
                onClick={() => handlePickCandidate(c)}
                className="text-left text-sm border border-gray-200 rounded-lg px-3 py-2 hover:border-indigo-400 hover:bg-indigo-50 transition"
              >
                {c}
              </button>
            ))}
          </div>
        )}
        <button
          type="submit"
          disabled={loading}
          className="self-start bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
        >
          {loading ? 'Détection du flux...' : 'Ajouter la source'}
        </button>
      </form>

      <div className="flex flex-col gap-3">
        {sources.length === 0 && (
          <p className="text-gray-400 text-sm">Aucune source pour l&apos;instant.</p>
        )}
        {sources.map(source => (
          <div
            key={source.id}
            className="bg-white rounded-xl p-4 border border-gray-100 flex items-center justify-between gap-4"
          >
            <div className="min-w-0">
              <p className="font-medium text-gray-900">{source.name || 'Sans nom'}</p>
              <p className="text-sm text-gray-400 truncate">{source.url}</p>
              <p className="text-xs text-gray-400 mt-1">
                {source.articles_count} article{source.articles_count > 1 ? 's' : ''} · Dernière sync : {relativeTime(source.last_crawled)}
              </p>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className={`text-xs px-3 py-1 rounded-full font-medium ${STATUS_COLORS[source.status] ?? 'bg-gray-100 text-gray-500'}`}>
                {STATUS_LABELS[source.status] ?? source.status}
              </span>
              <button
                onClick={() => handleScrape(source.id)}
                className="text-xs bg-indigo-600 text-white px-3 py-1 rounded-full hover:bg-indigo-700 transition"
              >
                Scraper
              </button>
              <button
                onClick={() => handleDelete(source.id)}
                className="text-xs bg-red-50 text-red-500 px-3 py-1 rounded-full hover:bg-red-100 transition"
              >
                Supprimer
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
