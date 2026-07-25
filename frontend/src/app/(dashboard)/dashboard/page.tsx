'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'

export default function DashboardPage() {
  const [email, setEmail] = useState('')
  const supabase = createClient()

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (data.user) setEmail(data.user.email ?? '')
    })
  }, [])

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Bonjour 👋</h1>
        <p className="text-gray-500 mt-1">{email}</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Sources actives', value: '0' },
          { label: 'Posts générés', value: '0' },
          { label: 'Publications ce mois', value: '0' },
        ].map(stat => (
          <div key={stat.label} className="bg-white rounded-xl p-6 border border-gray-100">
            <p className="text-sm text-gray-500">{stat.label}</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl p-6 border border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Activité récente</h2>
        <p className="text-gray-400 text-sm">Aucune activité pour l&apos;instant — commence par ajouter une source.</p>
      </div>
    </div>
  )
}