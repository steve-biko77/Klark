'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'

const navItems = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Sources', href: '/sources' },
  { label: 'Articles', href: '/articles' },
  { label: 'Posts', href: '/posts' },
  { label: 'Calendrier', href: '/calendar' },
  { label: 'Analytics', href: '/analytics' },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const supabase = createClient()

  async function handleLogout() {
    await supabase.auth.signOut()
    router.push('/login')
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 bg-white border-r border-gray-100 flex flex-col py-6 px-4 gap-2">
        <h1 className="text-xl font-bold text-indigo-600 mb-6 px-2">Klark</h1>

        <nav className="flex flex-col gap-1 flex-1">
          {navItems.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition
                ${pathname === item.href
                  ? 'bg-indigo-50 text-indigo-600'
                  : 'text-gray-600 hover:bg-gray-50'
                }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <button
          onClick={handleLogout}
          className="px-3 py-2 text-sm text-gray-500 hover:text-red-500 text-left transition"
        >
          Déconnexion
        </button>
      </aside>

      <main className="flex-1 bg-gray-50 p-8">
        {children}
      </main>
    </div>
  )
}