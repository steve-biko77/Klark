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

export function getUsername(): string {
  if (typeof document === 'undefined') return ''
  const match = document.cookie.match(/(^| )username=([^;]+)/)
  return match ? decodeURIComponent(match[2]) : ''
}

/** Étape 1 de la 2FA — retourne {status:'otp_sent', user_id, email, username} */
export async function login(username: string, password: string) {
  const res = await fetch(`${BASE_URL}/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error ?? 'Identifiants incorrects')
  }
  return res.json() as Promise<{ status: string; user_id: number; email: string; username: string }>
}

/** Étape 2 de la 2FA — vérifie le code OTP et stocke les tokens */
export async function verifyOTP(user_id: number, code: string, username: string) {
  const res = await fetch(`${BASE_URL}/auth/verify-otp/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id, code }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error ?? 'Code invalide')
  }
  const data = await res.json()
  setCookie('access_token', data.access, 1)
  setCookie('refresh_token', data.refresh, 7)
  setCookie('username', username, 7)
  return data
}

/** Renvoie un nouveau code OTP */
export async function resendOTP(user_id: number) {
  const res = await fetch(`${BASE_URL}/auth/resend-otp/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id }),
  })
  if (!res.ok) throw new Error('Erreur lors de l\'envoi du code')
  return res.json()
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

/** Demande un lien de reset par email */
export async function requestPasswordReset(email: string) {
  const res = await fetch(`${BASE_URL}/auth/password-reset/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!res.ok) throw new Error('Erreur lors de la demande')
  return res.json()
}

/** Confirme le nouveau mot de passe avec uid + token */
export async function confirmPasswordReset(uid: string, token: string, new_password: string) {
  const res = await fetch(`${BASE_URL}/auth/password-reset-confirm/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ uid, token, new_password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error ?? 'Lien invalide ou expiré')
  }
  return res.json()
}
