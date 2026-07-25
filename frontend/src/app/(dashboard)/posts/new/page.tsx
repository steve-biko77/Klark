'use client'

import { Suspense, useState } from 'react'
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

function NewPostForm() {
  const [postId, setPostId] = useState<number | null>(null)
  const [content, setContent] = useState('')
  const [platform, setPlatform] = useState('linkedin')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [generated, setGenerated] = useState(false)
  const router = useRouter()
  const searchParams = useSearchParams()
  const article_id = searchParams.get('article_id')

  async function handleGenerate() {
    setLoading(true)
    try {
      const token = getToken()
      const result = await apiFetch('/posts/generate/', token, {
        method: 'POST',
        body: JSON.stringify({ article_id, platform }),
      })
      setPostId(result.id)
      setContent(result.content)
      setGenerated(true)
    } catch {
      alert('Erreur lors de la generation')
    }
    setLoading(false)
  }

  async function handleSave() {
    if (!postId) return
    setSaving(true)
    try {
      const token = getToken()
      await apiFetch(`/posts/${postId}/`, token, {
        method: 'PATCH',
        body: JSON.stringify({ content }),
      })
      router.push('/posts')
    } catch {
      alert('Erreur lors de la sauvegarde')
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Generer un post</h1>
        <p className="text-gray-500 mt-1">Klark va transformer l'article en post pret a publier</p>
      </div>

      <div className="bg-white rounded-xl p-6 border border-gray-100 flex flex-col gap-4">
        <div>
          <label className="text-sm font-medium text-gray-700 mb-1 block">Plateforme</label>
          <select
            value={platform}
            onChange={e => setPlatform(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="linkedin">LinkedIn</option>
            <option value="twitter">Twitter / X</option>
            <option value="blog">Blog</option>
          </select>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 transition disabled:opacity-50"
        >
          {loading ? 'Generation en cours...' : 'Generer avec Klark'}
        </button>
      </div>

      {generated && (
        <div className="bg-white rounded-xl p-6 border border-gray-100 flex flex-col gap-4">
          <h2 className="text-lg font-semibold text-gray-900">Post genere</h2>
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            rows={10}
            className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          />
          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
            >
              {saving ? 'Sauvegarde...' : 'Sauvegarder et voir mes posts'}
            </button>
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="flex-1 border border-gray-200 text-gray-600 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition disabled:opacity-50"
            >
              Regenerer
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
