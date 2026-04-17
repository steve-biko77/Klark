'use client'

import { useEffect, useState } from 'react'
import { getToken } from '@/lib/auth'
import { apiFetch } from '@/lib/api'

type Post = {
  id: string
  content: string
  platform: string
  status: string
  created_at: string
}

export default function PostsPage() {
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)

  async function loadPosts() {
    const token = getToken()
    const data = await apiFetch('/posts/', token)
    setPosts(data)
    setLoading(false)
  }

  useEffect(() => { loadPosts() }, [])

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
              <span className="text-xs bg-indigo-50 text-indigo-600 px-3 py-1 rounded-full font-medium">
                {post.platform}
              </span>
              <span className="text-xs text-gray-400">
                {new Date(post.created_at).toLocaleDateString('fr-FR')}
              </span>
            </div>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{post.content}</p>
            <div className="flex items-center gap-2">
              <span className="text-xs bg-gray-100 text-gray-500 px-3 py-1 rounded-full">
                {post.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
