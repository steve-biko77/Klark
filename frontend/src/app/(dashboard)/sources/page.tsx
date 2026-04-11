'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'
import { apiFetch } from '@/lib/api'

type Source = {
  id: string
  url: string
  name: string
  status: string
  created_at: string
}

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([])
  const [url, setUrl] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const supabase = createClient()

  async function getToken() {
    const { data } = await supabase.auth.getSession()
    return data.session?.access_token ?? ''
  }

  async function loadSources() {
    const token = await getToken()
    const data = await apiFetch('/sources/', token)
    setSources(data)
  }

  useEffect(() => { loadSources() }, [])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const token = await getToken()
      await apiFetch('/sources/', token, {
        method: 'POST',
        body: JSON.stringify({ url, name }),
      })
      setUrl('')
      setName('')
      await loadSources()
    } catch {
      setError('Erreur lors de l\'ajout de la source')
    }
    setLoading(false)
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sources</h1>
        <p className="text-gray-500 mt-1">Ajoute les flux RSS que Klark va surveiller</p>
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
            <label className="text-sm font-medium text-gray-700 mb-1 block">URL RSS</label>
            <input
              type="url"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://exemple.com/rss"
              required
              className="w-full border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="self-start bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
        >
          {loading ? 'Ajout...' : 'Ajouter la source'}
        </button>
      </form>

      <div className="flex flex-col gap-3">
        {sources.length === 0 && (
          <p className="text-gray-400 text-sm">Aucune source pour l'instant.</p>
        )}
        {sources.map(source => (
          <div key={source.id} className="bg-white rounded-xl p-4 border border-gray-100 flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900">{source.name || 'Sans nom'}</p>
              <p className="text-sm text-gray-400">{source.url}</p>
            </div>
            <span className="text-xs bg-gray-100 text-gray-500 px-3 py-1 rounded-full">
              {source.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}