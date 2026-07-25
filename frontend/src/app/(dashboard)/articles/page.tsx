'use client'

import { useEffect, useState } from 'react'
import { getToken } from '@/lib/auth'
import { apiFetch } from '@/lib/api'
import { useRouter } from 'next/navigation'

type Article = {
  id: string
  title: string
  url: string
  content: string
  excerpt: string
  score: number
  published_at: string | null
  created_at: string
  source_id: string
  source_name: string
}

const RELATIVE_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 60 * 60 * 24 * 365],
  ['month', 60 * 60 * 24 * 30],
  ['day', 60 * 60 * 24],
  ['hour', 60 * 60],
  ['minute', 60],
]
const relativeFormatter = new Intl.RelativeTimeFormat('fr', { numeric: 'auto' })

function formatRelativeDate(dateString: string): string {
  const diffSeconds = (new Date(dateString).getTime() - Date.now()) / 1000
  for (const [unit, secondsInUnit] of RELATIVE_UNITS) {
    if (Math.abs(diffSeconds) >= secondsInUnit) {
      return relativeFormatter.format(Math.round(diffSeconds / secondsInUnit), unit)
    }
  }
  return relativeFormatter.format(Math.round(diffSeconds / 60), 'minute')
}

function scoreBadgeStyle(score: number): string {
  if (score > 70) return 'bg-green-50 text-green-700 border border-green-200'
  if (score >= 40) return 'bg-amber-50 text-amber-700 border border-amber-200'
  return 'bg-red-50 text-red-700 border border-red-200'
}

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [sortByScore, setSortByScore] = useState(false)
  const [relevantOnly, setRelevantOnly] = useState(false)
  const router = useRouter()

  async function loadArticles() {
    const token = getToken()
    const data = await apiFetch('/articles/', token)
    setArticles(data)
    setLoading(false)
  }

  useEffect(() => { loadArticles() }, [])

  const displayedArticles = articles
    .filter(a => !relevantOnly || a.score > 70)
    .sort((a, b) => (sortByScore ? b.score - a.score : 0))

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Articles</h1>
        <p className="text-gray-500 mt-1">Articles collectes par Klark depuis tes sources</p>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => setSortByScore(s => !s)}
          className={`text-xs px-3 py-1.5 rounded-full font-medium border transition ${
            sortByScore
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'
          }`}
        >
          Trier par score
        </button>
        <button
          onClick={() => setRelevantOnly(r => !r)}
          className={`text-xs px-3 py-1.5 rounded-full font-medium border transition ${
            relevantOnly
              ? 'bg-green-600 text-white border-green-600'
              : 'bg-white text-gray-600 border-gray-200 hover:border-green-300'
          }`}
        >
          Pertinents uniquement
        </button>
      </div>

      {loading && <p className="text-gray-400 text-sm">Chargement...</p>}

      <div className="flex flex-col gap-3">
        {displayedArticles.length === 0 && !loading && (
          <p className="text-gray-400 text-sm">Aucun article — scrape une source dabord.</p>
        )}
        {displayedArticles.map(article => (
          <div key={article.id} className="bg-white rounded-xl p-5 border border-gray-100 flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-gray-900 hover:text-indigo-600 transition"
                >
                  {article.title}
                </a>
                {article.score > 0 && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${scoreBadgeStyle(article.score)}`}>
                    {Math.round(article.score)}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-400 mt-1">{article.excerpt}</p>
              <div className="flex gap-3 mt-2 text-xs text-gray-400">
                {article.source_name && <span>{article.source_name}</span>}
                <span>{formatRelativeDate(article.published_at ?? article.created_at)}</span>
              </div>
            </div>
            <button
              onClick={() => router.push(`/posts/new?article_id=${article.id}`)}
              className="shrink-0 text-xs bg-indigo-600 text-white px-3 py-2 rounded-lg hover:bg-indigo-700 transition"
            >
              Generer post
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
