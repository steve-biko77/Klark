const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function refreshAccessToken(): Promise<string | null> {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(/(^| )refresh_token=([^;]+)/)
  const refreshToken = match ? match[2] : null
  if (!refreshToken) return null

  const res = await fetch(`${BASE_URL}/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: refreshToken }),
  })
  if (!res.ok) return null

  const data = await res.json()
  const expires = new Date(Date.now() + 86400 * 1000).toUTCString()
  document.cookie = `access_token=${data.access}; expires=${expires}; path=/; SameSite=Lax`
  return data.access
}

export async function apiFetch(path: string, token: string, options: RequestInit = {}) {
  // FormData (upload de fichier) : laisser le navigateur poser son propre
  // Content-Type (multipart/form-data; boundary=...), sinon l'upload échoue.
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData

  const makeRequest = (t: string) =>
    fetch(`${BASE_URL}${path}`, {
      ...options,
      redirect: 'follow',
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        'Authorization': `Bearer ${t}`,
        ...options.headers,
      },
    })

  let res = await makeRequest(token)

  if (res.status === 401) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      res = await makeRequest(newToken)
    } else {
      if (typeof window !== 'undefined') {
        window.location.href = '/login?expired=1'
      }
      throw new Error('Session expirée')
    }
  }

  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

function currentToken(): string {
  if (typeof document === 'undefined') return ''
  const match = document.cookie.match(/(^| )access_token=([^;]+)/)
  return match ? match[2] : ''
}

export const api = {
  get: (path: string) => apiFetch(path, currentToken()),
  post: (path: string, data: unknown) =>
    apiFetch(path, currentToken(), { method: 'POST', body: JSON.stringify(data) }),
  patch: (path: string, data: unknown) =>
    apiFetch(path, currentToken(), { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (path: string) => apiFetch(path, currentToken(), { method: 'DELETE' }),
}
