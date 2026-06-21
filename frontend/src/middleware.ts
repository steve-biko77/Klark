import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_PATHS = ['/login', '/register', '/forgot-password', '/reset-password', '/verify-otp']

export function middleware(req: NextRequest) {
  const token = req.cookies.get('access_token')?.value
  const pathname = req.nextUrl.pathname

  const isPublicPath = PUBLIC_PATHS.some(p => pathname.startsWith(p))

  if (!token && !isPublicPath && pathname !== '/') {
    return NextResponse.redirect(new URL('/login', req.url))
  }

  if (token && (pathname.startsWith('/login') || pathname.startsWith('/register'))) {
    return NextResponse.redirect(new URL('/dashboard', req.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
