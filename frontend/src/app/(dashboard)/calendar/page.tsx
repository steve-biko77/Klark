'use client'

import { useEffect, useState, useCallback } from 'react'
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

type CalendarData = Record<string, Post[]>

const HOURS = Array.from({ length: 17 }, (_, i) => i + 6)
const DAY_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']

const PLATFORM_STYLES: Record<string, string> = {
  linkedin: 'bg-blue-100 text-blue-700 border border-blue-200',
  twitter: 'bg-sky-100 text-sky-700 border border-sky-200',
  blog: 'bg-violet-100 text-violet-700 border border-violet-200',
}

function getMondayOfWeek(date: Date): Date {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  const day = d.getDay()
  const diff = day === 0 ? -6 : 1 - day
  d.setDate(d.getDate() + diff)
  return d
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

function toWeekParam(date: Date): string {
  return date.toISOString().slice(0, 10)
}

export default function CalendarPage() {
  const [weekStart, setWeekStart] = useState<Date>(() => getMondayOfWeek(new Date()))
  const [calendarData, setCalendarData] = useState<CalendarData>({})
  const [draftPosts, setDraftPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState<{ date: string; hour: number } | null>(null)
  const [selectedPostId, setSelectedPostId] = useState('')
  const [modalTime, setModalTime] = useState('')
  const [scheduling, setScheduling] = useState(false)
  const [conflict, setConflict] = useState<{ conflicting_time: string } | null>(null)

  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i))

  const loadCalendar = useCallback(async () => {
    setLoading(true)
    const token = getToken()
    try {
      const data = await apiFetch(`/posts/calendar/?week=${toWeekParam(weekStart)}`, token!)
      setCalendarData(data)
    } catch {
      setCalendarData({})
    }
    setLoading(false)
  }, [weekStart])

  const loadDrafts = useCallback(async () => {
    const token = getToken()
    try {
      const data: Post[] = await apiFetch('/posts/', token!)
      setDraftPosts(data.filter(p => p.status === 'draft'))
    } catch {
      setDraftPosts([])
    }
  }, [])

  useEffect(() => {
    loadCalendar()
    loadDrafts()
  }, [loadCalendar, loadDrafts])

  function getPostsInSlot(day: Date, hour: number): Post[] {
    const dayKey = toWeekParam(day)
    const dayPosts = calendarData[dayKey] ?? []
    return dayPosts.filter(post => {
      if (!post.scheduled_at) return false
      return new Date(post.scheduled_at).getUTCHours() === hour
    })
  }

  function openModal(day: Date, hour: number) {
    setModal({ date: toWeekParam(day), hour })
    setModalTime(`${String(hour).padStart(2, '0')}:00`)
    setSelectedPostId('')
    setConflict(null)
  }

  async function handleSchedule(force = false) {
    if (!modal || !selectedPostId || !modalTime) return
    setScheduling(true)
    const token = getToken()
    try {
      const result = await apiFetch(`/posts/${selectedPostId}/schedule/`, token!, {
        method: 'PATCH',
        body: JSON.stringify({
          scheduled_at: `${modal.date}T${modalTime}:00`,
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
      await Promise.all([loadCalendar(), loadDrafts()])
    } catch {
      alert('Erreur lors de la planification')
    }
    setScheduling(false)
  }

  const weekLabel = `${weekDays[0].toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })} — ${weekDays[6].toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })}`

  function modalDayLabel(): string {
    if (!modal) return ''
    const [y, m, d] = modal.date.split('-').map(Number)
    return new Date(y, m - 1, d).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Calendrier éditorial</h1>
          <p className="text-gray-500 mt-1">{weekLabel}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setWeekStart(prev => addDays(prev, -7))}
            className="px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition"
          >
            ← Précédente
          </button>
          <button
            onClick={() => setWeekStart(getMondayOfWeek(new Date()))}
            className="px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition"
          >
            Aujourd&apos;hui
          </button>
          <button
            onClick={() => setWeekStart(prev => addDays(prev, 7))}
            className="px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition"
          >
            Suivante →
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 overflow-auto">
        {loading ? (
          <p className="text-gray-400 text-sm p-8">Chargement...</p>
        ) : (
          <table className="w-full table-fixed border-collapse min-w-[700px]">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="w-14 p-2 border-r border-gray-100" />
                {weekDays.map((day, i) => {
                  const isToday = day.toDateString() === new Date().toDateString()
                  return (
                    <th key={i} className="p-3 text-center border-r border-gray-100 last:border-r-0">
                      <div className="text-xs text-gray-400 font-medium">{DAY_LABELS[i]}</div>
                      <div className={`text-sm font-bold mt-0.5 ${isToday ? 'text-indigo-600' : 'text-gray-900'}`}>
                        {day.getDate()}
                      </div>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {HOURS.map(hour => (
                <tr key={hour} className="border-b border-gray-50 last:border-b-0">
                  <td className="p-2 text-xs text-gray-400 font-mono border-r border-gray-100 text-center align-top pt-2 w-14">
                    {String(hour).padStart(2, '0')}h
                  </td>
                  {weekDays.map((day, di) => {
                    const slotPosts = getPostsInSlot(day, hour)
                    const platformCounts = slotPosts.reduce<Record<string, number>>((acc, p) => {
                      acc[p.platform] = (acc[p.platform] ?? 0) + 1
                      return acc
                    }, {})
                    const hasConflict = Object.values(platformCounts).some(count => count >= 2)
                    return (
                      <td
                        key={di}
                        onClick={() => openModal(day, hour)}
                        className={`p-1 align-top h-12 cursor-pointer hover:bg-gray-50 transition border-r border-gray-50 last:border-r-0 ${hasConflict ? 'ring-1 ring-inset ring-red-400' : ''}`}
                      >
                        <div className="flex flex-col gap-0.5">
                          {slotPosts.map(post => (
                            <div
                              key={post.id}
                              onClick={e => e.stopPropagation()}
                              className={`rounded px-1.5 py-1 text-[10px] leading-tight ${PLATFORM_STYLES[post.platform] ?? 'bg-gray-100 text-gray-700 border border-gray-200'}`}
                            >
                              <span className="font-bold uppercase tracking-wide">{post.platform}</span>
                              <br />
                              <span>{post.content.slice(0, 50)}</span>
                            </div>
                          ))}
                        </div>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="flex items-center gap-5 text-xs text-gray-500">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-blue-100 border border-blue-200 inline-block" />
          LinkedIn
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-sky-100 border border-sky-200 inline-block" />
          Twitter
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-violet-100 border border-violet-200 inline-block" />
          Blog
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded ring-1 ring-red-400 inline-block" />
          Conflit horaire
        </span>
        <span className="text-gray-400">Cliquer sur un créneau pour programmer un post</span>
      </div>

      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl flex flex-col gap-5">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Programmer un post</h2>
              <p className="text-sm text-gray-500 mt-1 capitalize">{modalDayLabel()}</p>
            </div>

            <div className="flex flex-col gap-4">
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">Post à programmer</label>
                {draftPosts.length === 0 ? (
                  <p className="text-sm text-gray-400 py-2">Aucun post en brouillon disponible.</p>
                ) : (
                  <select
                    value={selectedPostId}
                    onChange={e => setSelectedPostId(e.target.value)}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Choisir un post...</option>
                    {draftPosts.map(post => (
                      <option key={post.id} value={post.id}>
                        [{post.platform}] {post.content.slice(0, 60)}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">Heure</label>
                <input
                  type="time"
                  value={modalTime}
                  onChange={e => setModalTime(e.target.value)}
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
                disabled={scheduling || !selectedPostId || !modalTime}
                className="px-6 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
              >
                {scheduling ? 'Planification...' : 'Programmer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
