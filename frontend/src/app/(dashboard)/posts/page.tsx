'use client'

import { useEffect, useState } from 'react'
import { getToken } from '@/lib/auth'
import { apiFetch } from '@/lib/api'

type Post = {
  id: string
  content: string
  platform: string
  status: string
  scheduled_at: string | null
  created_at: string
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Brouillon',
  scheduled: 'Planifié',
  published: 'Publié',
  failed: 'Échoué',
}

const PLATFORM_STYLES: Record<string, string> = {
  linkedin: 'bg-blue-50 text-blue-600',
  twitter: 'bg-sky-50 text-sky-600',
  blog: 'bg-violet-50 text-violet-600',
}

function canReschedule(post: Post): boolean {
  if (post.status !== 'scheduled' || !post.scheduled_at) return false
  return new Date(post.scheduled_at).getTime() - Date.now() > 60 * 60 * 1000
}

export default function PostsPage() {
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState<Post | null>(null)
  const [schedDate, setSchedDate] = useState('')
  const [schedTime, setSchedTime] = useState('')
  const [scheduling, setScheduling] = useState(false)

  async function loadPosts() {
    const token = getToken()
    const data = await apiFetch('/posts/', token!)
    setPosts(data)
    setLoading(false)
  }

  useEffect(() => { loadPosts() }, [])

  function openModal(post: Post) {
    if (post.scheduled_at) {
      const d = new Date(post.scheduled_at)
      setSchedDate(d.toISOString().slice(0, 10))
      setSchedTime(d.toISOString().slice(11, 16))
    } else {
      const tomorrow = new Date()
      tomorrow.setDate(tomorrow.getDate() + 1)
      setSchedDate(tomorrow.toISOString().slice(0, 10))
      setSchedTime('09:00')
    }
    setModal(post)
  }

  async function handleSchedule() {
    if (!modal || !schedDate || !schedTime) return
    setScheduling(true)
    const token = getToken()
    try {
      await apiFetch(`/posts/${modal.id}/schedule/`, token!, {
        method: 'PATCH',
        body: JSON.stringify({ scheduled_at: `${schedDate}T${schedTime}:00` }),
      })
      setModal(null)
      await loadPosts()
    } catch {
      alert('Erreur lors de la planification')
    }
    setScheduling(false)
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mes posts</h1>
        <p className="text-gray-500 mt-1">Posts generes par Klark</p>
      </div>

      {loading && <p className="text-gray-400 text-sm">Chargement...</p>}

      <div className="flex flex-col gap-4">
        {posts.length === 0 && !loading && (
          <p className="text-gray-400 text-sm">Aucun post — genere-en un depuis la page Articles.</p>
        )}
        {posts.map(post => (
          <div key={post.id} className="bg-white rounded-xl p-6 border border-gray-100 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className={`text-xs px-3 py-1 rounded-full font-medium ${PLATFORM_STYLES[post.platform] ?? 'bg-indigo-50 text-indigo-600'}`}>
                {post.platform}
              </span>
              <span className="text-xs text-gray-400">
                {new Date(post.created_at).toLocaleDateString('fr-FR')}
              </span>
            </div>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{post.content}</p>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs bg-gray-100 text-gray-500 px-3 py-1 rounded-full">
                  {STATUS_LABELS[post.status] ?? post.status}
                </span>
                {post.scheduled_at && (
                  <span className="text-xs text-gray-400">
                    Prévu le {new Date(post.scheduled_at).toLocaleString('fr-FR', {
                      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
                    })}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {post.status === 'draft' && (
                  <button
                    onClick={() => openModal(post)}
                    className="text-xs bg-indigo-600 text-white px-3 py-1 rounded-full hover:bg-indigo-700 transition"
                  >
                    Programmer
                  </button>
                )}
                {canReschedule(post) && (
                  <button
                    onClick={() => openModal(post)}
                    className="text-xs bg-amber-50 text-amber-600 border border-amber-200 px-3 py-1 rounded-full hover:bg-amber-100 transition"
                  >
                    Reprogrammer
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-xl flex flex-col gap-5">
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                {modal.status === 'scheduled' ? 'Reprogrammer' : 'Programmer'} le post
              </h2>
              <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                {modal.content.slice(0, 80)}{modal.content.length > 80 ? '…' : ''}
              </p>
            </div>

            <div className="flex flex-col gap-3">
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">Date</label>
                <input
                  type="date"
                  value={schedDate}
                  onChange={e => setSchedDate(e.target.value)}
                  min={new Date().toISOString().slice(0, 10)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">Heure</label>
                <input
                  type="time"
                  value={schedTime}
                  onChange={e => setSchedTime(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setModal(null)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition"
              >
                Annuler
              </button>
              <button
                onClick={handleSchedule}
                disabled={scheduling || !schedDate || !schedTime}
                className="px-6 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
              >
                {scheduling ? 'Planification...' : (modal.status === 'scheduled' ? 'Reprogrammer' : 'Programmer')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
