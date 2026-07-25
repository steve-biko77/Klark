'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getToken, getUsername } from '@/lib/auth'
import { apiFetch } from '@/lib/api'

type Stats = {
  sources_actives: number
  posts_generes: number
  articles: number
}

export default function DashboardPage() {
  const [username, setUsername] = useState('')
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    setUsername(getUsername())
    const token = getToken()
    apiFetch('/dashboard/stats/', token)
      .then(data => setStats(data))
      .catch(() => setStats({ sources_actives: 0, posts_generes: 0, articles: 0 }))
  }, [])

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
