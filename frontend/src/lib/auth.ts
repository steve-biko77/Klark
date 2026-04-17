const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

function setCookie(name: string, value: string, days: number) {
  const expires = new Date(Date.now() + days * 86400 * 1000).toUTCString()
  document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax`
}

function deleteCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`
}

export function getToken(): string {
  if (typeof document === 'undefined') return ''
  const match = document.cookie.match(/(^| )access_token=([^;]+)/)
  return match ? match[2] : ''
}

export async function login(username: string, password: string) {
  const res = await fetch(`${BASE_URL}/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) throw new Error('Identifiants incorrects')
  const data = await res.json()
  setCookie('access_token', data.access, 1)
  setCookie('refresh_token', data.refresh, 7)
  setCookie('username', username, 7)
  return data
}

export async function register(username: string, email: string, password: string) {
  const res = await fetch(`${BASE_URL}/auth/register/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  })
  if (!res.ok) {
    const err = await res.json()
    const firstError = Object.values(err)[0]
    throw new Error(Array.isArray(firstError) ? firstError[0] : String(firstError))
  }
  const data = await res.json()
  setCookie('access_token', data.access, 1)
  setCookie('refresh_token', data.refresh, 7)
  setCookie('username', username, 7)
  return data
}

export function logout() {
  deleteCookie('access_token')
  deleteCookie('refresh_token')
  deleteCookie('username')
}

export function getUsername(): string {
  if (typeof document === 'undefined') return ''
  const match = document.cookie.match(/(^| )username=([^;]+)/)
  return match ? decodeURIComponent(match[2]) : ''
}
