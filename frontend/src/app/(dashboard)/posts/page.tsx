'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
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

const STATUS_TABS: { label: string; value: string }[] = [
  { label: 'Tous', value: '' },
  { label: 'Brouillons', value: 'draft' },
  { label: 'Programmés', value: 'scheduled' },
  { label: 'Publiés', value: 'published' },
  { label: 'Échoués', value: 'failed' },
]

const STATUS_LABELS: Record<string, string> = {
  draft: 'Brouillon',
  scheduled: 'Planifié',
  published: 'Publié',
  failed: 'Échoué',
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600',
  scheduled: 'bg-blue-100 text-blue-700',
  published: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

const PLATFORM_STYLES: Record<string, string> = {
  linkedin: 'bg-blue-50 text-blue-600',
  twitter: 'bg-sky-50 text-sky-600',
  blog: 'bg-violet-50 text-violet-600',
}

const PLATFORM_ICONS: Record<string, string> = {
  linkedin: '💼',
  twitter: '🐦',
  blog: '📝',
}

const EXCERPT_LENGTH = 100

function canReschedule(post: Post): boolean {
  if (post.status !== 'scheduled' || !post.scheduled_at) return false
  return new Date(post.scheduled_at).getTime() - Date.now() > 60 * 60 * 1000
}

export default function PostsPage() {
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [modal, setModal] = useState<Post | null>(null)
  const [schedDate, setSchedDate] = useState('')
  const [schedTime, setSchedTime] = useState('')
  const [scheduling, setScheduling] = useState(false)
  const [conflict, setConflict] = useState<{ conflicting_time: string } | null>(null)

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
    setConflict(null)
    setModal(post)
  }

  async function handleCancel(post: Post) {
    if (!confirm('Annuler cette programmation ?')) return
    const token = getToken()
    try {
      await apiFetch(`/posts/${post.id}/cancel/`, token!, { method: 'POST' })
      await loadPosts()
    } catch {
      alert('Erreur lors de l\'annulation')
    }
  }

  async function handleRetry(post: Post) {
    const token = getToken()
    try {
      await apiFetch(`/posts/${post.id}/retry/`, token!, { method: 'POST' })
      await loadPosts()
    } catch {
      alert('Erreur lors de la nouvelle tentative')
    }
  }

  async function handleSchedule(force = false) {
    if (!modal || !schedDate || !schedTime) return
    setScheduling(true)
    const token = getToken()
    try {
      const result = await apiFetch(`/posts/${modal.id}/schedule/`, token!, {
        method: 'PATCH',
        body: JSON.stringify({
          scheduled_at: `${schedDate}T${schedTime}:00`,
          force_conflict: force,
        }),
      })
      if (result.warning && !force) {
        setConflict(result)
        setScheduling(false)
        return
      }
      setConflict(null)
      setModal(null)
      await loadPosts()
    } catch {
      alert('Erreur lors de la planification')
    }
    setScheduling(false)
  }

  function toggleExpand(id: string) {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const filteredPosts = statusFilter ? posts.filter(p => p.status === statusFilter) : posts

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mes posts</h1>
          <p className="text-gray-500 mt-1">Posts generes par Klark</p>
        </div>
        <Link
          href="/posts/new"
          className="shrink-0 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition"
        >
          + Nouveau post
        </Link>
      </div>

      <div className="flex gap-2 border-b border-gray-100">
        {STATUS_TABS.map(tab => (
          <button
            key={tab.value}
            onClick={() => setStatusFilter(tab.value)}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px transition ${
              statusFilter === tab.value
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading && <p className="text-gray-400 text-sm">Chargement...</p>}

      <div className="flex flex-col gap-4">
        {filteredPosts.length === 0 && !loading && (
          <p className="text-gray-400 text-sm">Aucun post — genere-en un depuis la page Articles.</p>
        )}
        {filteredPosts.map(post => {
          const isExpanded = expandedIds.has(post.id)
          const isLong = post.content.length > EXCERPT_LENGTH
          const displayedContent = isExpanded || !isLong
            ? post.content
            : `${post.content.slice(0, EXCERPT_LENGTH)}…`

          return (
          <div key={post.id} className="bg-white rounded-xl p-6 border border-gray-100 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className={`text-xs px-3 py-1 rounded-full font-medium ${PLATFORM_STYLES[post.platform] ?? 'bg-indigo-50 text-indigo-600'}`}>
                {PLATFORM_ICONS[post.platform] ?? ''} {post.platform}
              </span>
              <span className="text-xs text-gray-400">
                {new Date(post.created_at).toLocaleDateString('fr-FR')}
              </span>
            </div>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">
              {displayedContent}
              {isLong && (
                <button
                  onClick={() => toggleExpand(post.id)}
                  className="ml-2 text-indigo-600 hover:underline text-xs font-medium"
                >
                  {isExpanded ? 'Afficher moins' : 'Afficher plus'}
                </button>
              )}
            </p>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`text-xs px-3 py-1 rounded-full font-medium ${STATUS_COLORS[post.status] ?? 'bg-gray-100 text-gray-500'}`}>
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
                  <Link
                    href={`/posts/new?edit_id=${post.id}`}
                    className="text-xs border border-gray-200 text-gray-600 px-3 py-1 rounded-full hover:bg-gray-50 transition"
                  >
                    Modifier
                  </Link>
                )}
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
                {post.status === 'scheduled' && (
                  <button
                    onClick={() => handleCancel(post)}
                    className="text-xs bg-red-50 text-red-500 border border-red-200 px-3 py-1 rounded-full hover:bg-red-100 transition"
                  >
                    Annuler
                  </button>
                )}
                {post.status === 'failed' && (
                  <>
                    <button
                      onClick={() => handleRetry(post)}
                      className="text-xs bg-indigo-600 text-white px-3 py-1 rounded-full hover:bg-indigo-700 transition"
                    >
                      Réessayer
                    </button>
                    <button
                      onClick={() => openModal(post)}
                      className="text-xs border border-gray-200 text-gray-600 px-3 py-1 rounded-full hover:bg-gray-50 transition"
                    >
                      Reprogrammer
                    </button>
                  </>
                )}
                {post.status === 'published' && (
                  <Link
                    href="/analytics"
                    title="Voir les analytics"
                    className="text-xs border border-gray-200 text-gray-600 px-3 py-1 rounded-full hover:bg-gray-50 transition"
                  >
                    📊 Analytics
                  </Link>
                )}
              </div>
            </div>
          </div>
          )
        })}
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

            {conflict && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-sm text-amber-700 flex flex-col gap-2">
                <span>
                  ⚠️ Conflit horaire : un autre post est déjà programmé à{' '}
                  {new Date(conflict.conflicting_time).toLocaleString('fr-FR', {
                    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
                  })} sur la même plateforme.
                </span>
                <button
                  onClick={() => handleSchedule(true)}
                  disabled={scheduling}
                  className="self-start px-3 py-1.5 bg-amber-600 text-white text-xs font-medium rounded-lg hover:bg-amber-700 transition disabled:opacity-50"
                >
                  Programmer quand même
                </button>
              </div>
            )}

            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setModal(null)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition"
              >
                Annuler
              </button>
              <button
                onClick={() => handleSchedule()}
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
