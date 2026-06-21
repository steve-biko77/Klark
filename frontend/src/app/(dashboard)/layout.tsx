'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { logout } from '@/lib/auth'

type NavItem = {
  label: string
  href: string
  icon?: React.ReactNode
}

function GearIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M19.14 12.94c.04-.3.06-.61.06-.94s-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96a7.08 7.08 0 0 0-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.48.48 0 0 0-.59.22L2.74 8.87a.47.47 0 0 0 .12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.47.47 0 0 0-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" />
    </svg>
  )
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Sources', href: '/sources' },
  { label: 'Articles', href: '/articles' },
  { label: 'Posts', href: '/posts' },
  { label: 'Calendrier', href: '/calendar' },
  { label: 'Analytics', href: '/analytics' },
  { label: 'Paramètres', href: '/settings', icon: <GearIcon /> },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()

  function handleLogout() {
    logout()
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
              className={`px-3 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2
                ${pathname === item.href
                  ? 'bg-indigo-50 text-indigo-600'
                  : 'text-gray-600 hover:bg-gray-50'
                }`}
            >
              {item.icon}
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
