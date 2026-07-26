'use client'

import { useEffect, useState } from 'react'
import { getToken } from '@/lib/auth'
import { apiFetch } from '@/lib/api'

type EvolutionPoint = { date: string; engagement_rate: number }

type PostAnalytics = {
  post_id: number
  platform: string
  published_at: string | null
  content_excerpt: string
  analytics_available: boolean
  likes: number | null
  views: number | null
  shares: number | null
  comments: number | null
  engagement_rate: number | null
  above_average: boolean | null
}

type Overview = {
  evolution_30j: EvolutionPoint[]
  total_views: number
  best_post: { post_id: number; engagement_rate: number } | null
  best_platform: string | null
  average_engagement_rate: number
  posts: PostAnalytics[]
}

type Recommendation = {
  dimension: string
  valeur_optimale: string
  engagement_moyen: number
  confiance: 'faible' | 'moyen' | 'fort'
}

type Recommendations = { recommendations: Recommendation[]; message: string | null }

const DIMENSION_LABELS: Record<string, string> = {
  longueur: 'Longueur du post',
  jour: 'Jour de publication',
  heure: 'Heure de publication',
  hashtags: 'Hashtags',
  question: 'Question dans le post',
}

const CONFIDENCE_STYLES: Record<string, string> = {
  faible: 'bg-gray-100 text-gray-500',
  moyen: 'bg-amber-100 text-amber-700',
  fort: 'bg-green-100 text-green-700',
}

function EvolutionChart({ points }: { points: EvolutionPoint[] }) {
  if (points.length === 0) {
    return <p className="text-sm text-gray-400">Pas encore assez de données pour tracer une courbe.</p>
  }
  const max = Math.max(...points.map(p => p.engagement_rate), 1)
  return (
    <div className="flex items-end gap-1 h-32">
      {points.map(p => (
        <div key={p.date} className="flex-1 flex flex-col items-center justify-end gap-1 group relative">
          <div
            className="w-full bg-indigo-500 rounded-t hover:bg-indigo-600 transition"
            style={{ height: `${Math.max((p.engagement_rate / max) * 100, 2)}%` }}
            title={`${p.date} — ${p.engagement_rate}%`}
          />
        </div>
      ))}
    </div>
  )
}

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [recommendations, setRecommendations] = useState<Recommendations | null>(null)
  const [loading, setLoading] = useState(true)
  const [collecting, setCollecting] = useState(false)
  const [toast, setToast] = useState('')

  async function load() {
    const token = getToken()
    const [ov, reco] = await Promise.all([
      apiFetch('/analytics/', token).catch(() => null),
      apiFetch('/analytics/recommendations/', token).catch(() => null),
    ])
    setOverview(ov)
    setRecommendations(reco)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  async function handleCollect() {
    setCollecting(true)
    const token = getToken()
    try {
      const result = await apiFetch('/analytics/collect/', token, { method: 'POST' })
      setToast(
        result.collected > 0
          ? `${result.collected} post${result.collected > 1 ? 's' : ''} mis à jour ✓`
          : 'Aucune nouvelle donnée disponible pour le moment.',
      )
      await load()
    } catch {
      setToast('Erreur lors de la collecte')
    }
    setCollecting(false)
    setTimeout(() => setToast(''), 4000)
  }

  if (loading) {
    return <p className="text-gray-400 text-sm">Chargement...</p>
  }

  const publishedPosts = overview?.posts ?? []
  const noDataAtAll = publishedPosts.length === 0

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-500 mt-1">Performance de vos posts publiés sur LinkedIn</p>
        </div>
        <button
          onClick={handleCollect}
          disabled={collecting}
          className="shrink-0 px-4 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-50 transition disabled:opacity-50"
        >
          {collecting ? 'Collecte...' : 'Rafraîchir les données'}
        </button>
      </div>

      {toast && (
        <div className="bg-indigo-50 border border-indigo-200 text-indigo-700 text-sm px-4 py-2 rounded-lg">
          {toast}
        </div>
      )}

      {noDataAtAll ? (
        <div className="bg-white rounded-xl border border-gray-100 p-10 text-center">
          <p className="text-gray-400 text-sm">
            Aucun post publié pour l&apos;instant. Une fois vos posts publiés sur LinkedIn, leurs métriques
            d&apos;engagement apparaîtront ici (déclenchez la collecte manuellement avec le bouton ci-dessus).
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <p className="text-sm text-gray-500">Vues cumulées (30j)</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{overview?.total_views ?? 0}</p>
            </div>
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <p className="text-sm text-gray-500">Engagement moyen</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{overview?.average_engagement_rate ?? 0}%</p>
            </div>
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <p className="text-sm text-gray-500">Meilleure plateforme</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{overview?.best_platform ?? '—'}</p>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 border border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Évolution de l&apos;engagement (30 jours)</h2>
            <EvolutionChart points={overview?.evolution_30j ?? []} />
          </div>

          <div className="bg-white rounded-xl p-6 border border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Ce qui marche pour vous</h2>
            {recommendations?.message ? (
              <p className="text-sm text-gray-400">{recommendations.message}</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {recommendations?.recommendations.map(r => (
                  <div key={`${r.dimension}-${r.valeur_optimale}`} className="border border-gray-100 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-gray-400">{DIMENSION_LABELS[r.dimension] ?? r.dimension}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${CONFIDENCE_STYLES[r.confiance]}`}>
                        {r.confiance}
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-gray-900 capitalize">{r.valeur_optimale}</p>
                    <p className="text-xs text-gray-500 mt-1">{r.engagement_moyen}% d&apos;engagement moyen</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Détail par post</h2>
            <div className="flex flex-col gap-3">
              {publishedPosts.map(p => (
                <div key={p.post_id} className="border border-gray-100 rounded-lg p-4 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm text-gray-700 truncate">{p.content_excerpt}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {p.platform} · {p.published_at ? new Date(p.published_at).toLocaleDateString('fr-FR') : '—'}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    {p.analytics_available ? (
                      <>
                        <p className="text-sm font-semibold text-gray-900">{p.engagement_rate}%</p>
                        <p className={`text-xs mt-0.5 ${p.above_average ? 'text-green-600' : 'text-gray-400'}`}>
                          {p.above_average ? '↑ au-dessus de votre moyenne' : '↓ en dessous de votre moyenne'}
                        </p>
                      </>
                    ) : (
                      <p className="text-xs text-gray-400">Analytics indisponibles</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
