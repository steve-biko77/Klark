'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { getToken, getUsername } from '@/lib/auth'
import { apiFetch } from '@/lib/api'

type Stats = {
  sources_actives: number
  posts_generes: number
  articles: number
}

type Notification = {
  id: number
  article_id: number
  article_title: string
  keyword: string
  is_read: boolean
  created_at: string
}

type BriefingSignal = {
  article_id: number
  article_title: string
  lines: string[]
}

type Briefing = {
  id: number
  date: string
  content: BriefingSignal[]
}

export default function DashboardPage() {
  const router = useRouter()
  const [username, setUsername] = useState('')
  const [stats, setStats] = useState<Stats | null>(null)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [briefing, setBriefing] = useState<Briefing | null>(null)

  useEffect(() => {
    setUsername(getUsername())
    const token = getToken()
    apiFetch('/dashboard/stats/', token)
      .then(data => setStats(data))
      .catch(() => setStats({ sources_actives: 0, posts_generes: 0, articles: 0 }))
    apiFetch('/notifications/', token)
      .then(data => setNotifications(data.filter((n: Notification) => !n.is_read)))
      .catch(() => setNotifications([]))
    apiFetch('/briefings/today/', token)
      .then(data => setBriefing(data))
      .catch(() => setBriefing(null))
  }, [])

  async function handleNotificationClick(notification: Notification) {
    const token = getToken()
    try {
      await apiFetch(`/notifications/${notification.id}/read/`, token, { method: 'PATCH' })
    } catch {
      // navigate anyway even if marking as read failed
    }
    setNotifications(prev => prev.filter(n => n.id !== notification.id))
    router.push(`/posts/new?article_id=${notification.article_id}`)
  }

  const cards = [
    { label: 'Sources actives', value: stats?.sources_actives ?? '—' },
    { label: 'Articles collectés', value: stats?.articles ?? '—' },
    { label: 'Posts générés', value: stats?.posts_generes ?? '—' },
  ]

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bonjour 👋</h1>
          <p className="text-gray-500 mt-1">{username}</p>
        </div>
        <Link
          href="/posts/new"
          className="shrink-0 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition"
        >
          + Nouveau post
        </Link>
      </div>

      {briefing && (
        <div className="bg-gradient-to-r from-indigo-600 to-indigo-700 rounded-xl p-6 flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <span className="text-lg">⚡</span>
            <h2 className="text-white font-semibold">Briefing flash du jour</h2>
          </div>
          {briefing.content.length === 0 || briefing.content.length < 3 ? (
            <p className="text-indigo-100 text-sm">
              {briefing.content.length === 0
                ? "Peu d'actualités pertinentes aujourd'hui."
                : `Peu d'actualités pertinentes aujourd'hui — ${briefing.content.length} ${briefing.content.length > 1 ? 'signaux' : 'signal'} seulement.`}
            </p>
          ) : null}
          {briefing.content.length > 0 && (
            <div className="flex flex-col gap-3">
              {briefing.content.map(signal => (
                <button
                  key={signal.article_id}
                  onClick={() => router.push(`/posts/new?article_id=${signal.article_id}`)}
                  className="text-left bg-white/10 hover:bg-white/20 rounded-lg p-4 transition"
                >
                  <p className="text-white font-medium text-sm mb-1">{signal.article_title}</p>
                  {signal.lines.map((line, i) => (
                    <p key={i} className="text-indigo-100 text-xs leading-relaxed">{line}</p>
                  ))}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {notifications.length > 0 && (
        <div className="flex flex-col gap-2">
          {notifications.map(notification => (
            <button
              key={notification.id}
              onClick={() => handleNotificationClick(notification)}
              className="text-left bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-center justify-between gap-4 hover:bg-amber-100 transition"
            >
              <span className="text-sm text-amber-800">
                🔔 <span className="font-medium">&quot;{notification.keyword}&quot;</span> détecté dans{' '}
                <span className="font-medium">{notification.article_title}</span>
              </span>
              <span className="text-xs text-amber-600 shrink-0">Générer un post →</span>
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        {cards.map(stat => (
          <div key={stat.label} className="bg-white rounded-xl p-6 border border-gray-100">
            <p className="text-sm text-gray-500">{stat.label}</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl p-6 border border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Activité récente</h2>
        <p className="text-gray-400 text-sm">
          {stats && (stats.sources_actives > 0 || stats.articles > 0)
            ? `${stats.sources_actives} source${stats.sources_actives > 1 ? 's' : ''} active${stats.sources_actives > 1 ? 's' : ''} · ${stats.articles} article${stats.articles > 1 ? 's' : ''} collecté${stats.articles > 1 ? 's' : ''} · ${stats.posts_generes} post${stats.posts_generes > 1 ? 's' : ''} généré${stats.posts_generes > 1 ? 's' : ''}`
            : 'Aucune activité pour l\'instant — commence par ajouter une source.'}
        </p>
      </div>
    </div>
  )
}
