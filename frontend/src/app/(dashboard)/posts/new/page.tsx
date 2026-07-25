'use client'

import { Suspense, useEffect, useState } from 'react'
import { getToken } from '@/lib/auth'
import { apiFetch } from '@/lib/api'
import { useRouter, useSearchParams } from 'next/navigation'

export default function NewPostPage() {
  return (
    <Suspense fallback={null}>
      <NewPostForm />
    </Suspense>
  )
}

const PLATFORM_LABELS: Record<string, string> = {
  linkedin: 'LinkedIn',
  twitter: 'Twitter / X',
  blog: 'Blog',
}

const PLATFORM_LIMITS: Record<string, number> = {
  linkedin: 1300,
  twitter: 280,
  blog: 3000,
}

type PlatformResult = {
  postId: number | null
  content: string
  error: string | null
  saving: boolean
  saved: boolean
}

function NewPostForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const article_id = searchParams.get('article_id')
  const edit_id = searchParams.get('edit_id')
  const isEditing = Boolean(edit_id)

  // --- Mode édition d'un brouillon existant (post unique) ---
  const [editPostId, setEditPostId] = useState<number | null>(null)
  const [editContent, setEditContent] = useState('')
  const [editSaving, setEditSaving] = useState(false)

  useEffect(() => {
    if (!edit_id) return
    const token = getToken()
    apiFetch(`/posts/${edit_id}/`, token)
      .then(post => {
        setEditPostId(post.id)
        setEditContent(post.content)
      })
      .catch(() => alert('Post introuvable'))
  }, [edit_id])

  async function handleSaveEdit() {
    if (!editPostId) return
    setEditSaving(true)
    try {
      const token = getToken()
      await apiFetch(`/posts/${editPostId}/`, token, {
        method: 'PATCH',
        body: JSON.stringify({ content: editContent }),
      })
      router.push('/posts')
    } catch {
      alert('Erreur lors de la sauvegarde')
      setEditSaving(false)
    }
  }

  // --- Mode génération (multi-plateforme) ---
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['linkedin'])
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<Record<string, PlatformResult>>({})
  const [activeTab, setActiveTab] = useState<string | null>(null)

  function togglePlatform(platform: string) {
    setSelectedPlatforms(prev =>
      prev.includes(platform) ? prev.filter(p => p !== platform) : [...prev, platform]
    )
  }

  async function handleGenerate() {
    if (selectedPlatforms.length === 0) return
    setLoading(true)
    try {
      const token = getToken()
      const response = await apiFetch('/posts/generate-multi/', token, {
        method: 'POST',
        body: JSON.stringify({ article_id, platforms: selectedPlatforms }),
      })
      const nextResults: Record<string, PlatformResult> = {}
      for (const r of response.results) {
        nextResults[r.platform] = {
          postId: r.id ?? null,
          content: r.content ?? '',
          error: r.error ?? null,
          saving: false,
          saved: false,
        }
      }
      setResults(nextResults)
      setActiveTab(selectedPlatforms[0])
    } catch {
      alert('Erreur lors de la generation')
    }
    setLoading(false)
  }

  function updateResultContent(platform: string, content: string) {
    setResults(prev => ({ ...prev, [platform]: { ...prev[platform], content } }))
  }

  async function handleSaveOne(platform: string) {
    const result = results[platform]
    if (!result?.postId) return
    setResults(prev => ({ ...prev, [platform]: { ...prev[platform], saving: true } }))
    try {
      const token = getToken()
      await apiFetch(`/posts/${result.postId}/`, token, {
        method: 'PATCH',
        body: JSON.stringify({ content: result.content }),
      })
      setResults(prev => ({ ...prev, [platform]: { ...prev[platform], saving: false, saved: true } }))
    } catch {
      alert(`Erreur lors de la sauvegarde (${PLATFORM_LABELS[platform]})`)
      setResults(prev => ({ ...prev, [platform]: { ...prev[platform], saving: false } }))
    }
  }

  async function handleSaveAll() {
    const platforms = Object.keys(results).filter(p => results[p].postId)
    await Promise.all(platforms.map(handleSaveOne))
    router.push('/posts')
  }

  const generatedPlatforms = Object.keys(results)

  if (isEditing) {
    return (
      <div className="flex flex-col gap-8 max-w-2xl">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Modifier le post</h1>
          <p className="text-gray-500 mt-1">Modifie le contenu puis sauvegarde</p>
        </div>
        <div className="bg-white rounded-xl p-6 border border-gray-100 flex flex-col gap-4">
          <textarea
            value={editContent}
            onChange={e => setEditContent(e.target.value)}
            rows={10}
            className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          />
          <button
            onClick={handleSaveEdit}
            disabled={editSaving}
            className="bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {editSaving ? 'Sauvegarde...' : 'Sauvegarder et voir mes posts'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Generer un post</h1>
        <p className="text-gray-500 mt-1">Klark va transformer l&apos;article en post pret a publier</p>
      </div>

      <div className="bg-white rounded-xl p-6 border border-gray-100 flex flex-col gap-4">
        <div>
          <label className="text-sm font-medium text-gray-700 mb-2 block">Plateformes</label>
          <div className="flex gap-2">
            {Object.keys(PLATFORM_LABELS).map(platform => (
              <label
                key={platform}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm cursor-pointer transition ${
                  selectedPlatforms.includes(platform)
                    ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 text-gray-600 hover:border-indigo-300'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedPlatforms.includes(platform)}
                  onChange={() => togglePlatform(platform)}
                  className="accent-indigo-600"
                />
                {PLATFORM_LABELS[platform]}
              </label>
            ))}
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading || selectedPlatforms.length === 0}
          className="bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 transition disabled:opacity-50"
        >
          {loading ? 'Generation en cours...' : 'Generer avec Klark'}
        </button>
      </div>

      {generatedPlatforms.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 flex flex-col">
          <div className="flex border-b border-gray-100">
            {generatedPlatforms.map(platform => (
              <button
                key={platform}
                onClick={() => setActiveTab(platform)}
                className={`px-4 py-3 text-sm font-medium border-b-2 -mb-px transition ${
                  activeTab === platform
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {PLATFORM_LABELS[platform]}
                {results[platform].error && ' ⚠️'}
              </button>
            ))}
          </div>

          {activeTab && results[activeTab] && (
            <div className="p-6 flex flex-col gap-4">
              {results[activeTab].error ? (
                <p className="text-sm text-red-500">
                  Erreur lors de la génération pour {PLATFORM_LABELS[activeTab]} : {results[activeTab].error}
                </p>
              ) : (
                <>
                  <textarea
                    value={results[activeTab].content}
                    onChange={e => updateResultContent(activeTab, e.target.value)}
                    rows={10}
                    className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                  />
                  <div className="flex items-center justify-between text-xs">
                    <span className={
                      results[activeTab].content.length > PLATFORM_LIMITS[activeTab]
                        ? 'text-red-500 font-medium'
                        : 'text-gray-400'
                    }>
                      {results[activeTab].content.length} / {PLATFORM_LIMITS[activeTab]} caractères
                    </span>
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={() => handleSaveOne(activeTab)}
                      disabled={results[activeTab].saving}
                      className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
                    >
                      {results[activeTab].saved
                        ? 'Enregistré ✓'
                        : results[activeTab].saving
                          ? 'Sauvegarde...'
                          : 'Sauvegarder cette version'}
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          <div className="p-6 pt-0">
            <button
              onClick={handleSaveAll}
              className="w-full border border-gray-200 text-gray-600 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
            >
              Tout sauvegarder et voir mes posts
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
