// The signed-in session, held outside React.
//
// client.ts needs the access token on every request and needs to refresh it on
// a 401, but it must not import a React context — so the tokens live in this
// module and AuthContext subscribes to it.
//
// The access token is memory-only. The refresh token is persisted, otherwise a
// page reload would sign the user out. localStorage means an XSS bug can read
// it; an httpOnly cookie would be safer but cannot be shared with a native
// client, which needs this same bearer flow.
import { API_BASE, API_PREFIX } from './config'
import type { AuthUser, TokenPair } from '../types'

const REFRESH_KEY = 'hhs.refresh_token'

let accessToken: string | null = null
let user: AuthUser | null = null

type Listener = (user: AuthUser | null) => void
const listeners = new Set<Listener>()

function emit() {
  for (const listener of listeners) listener(user)
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export const getAccessToken = () => accessToken
export const getUser = () => user

export function getRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY)
  } catch {
    // Private browsing modes can throw on access.
    return null
  }
}

export function setSession(pair: TokenPair) {
  accessToken = pair.access_token
  user = pair.user
  try {
    localStorage.setItem(REFRESH_KEY, pair.refresh_token)
  } catch {
    // Non-fatal: the session just will not survive a reload.
  }
  emit()
}

export function clearSession() {
  accessToken = null
  user = null
  try {
    localStorage.removeItem(REFRESH_KEY)
  } catch {
    /* ignore */
  }
  emit()
}

// Refresh tokens rotate: each one may be redeemed exactly once. Several
// requests failing with 401 at the same time would each try to refresh, and all
// but the first would be rejected — signing the user out mid-session. Sharing
// one in-flight promise is what prevents that.
let inFlight: Promise<boolean> | null = null

export function refreshSession(): Promise<boolean> {
  if (inFlight) return inFlight

  inFlight = (async () => {
    const refreshToken = getRefreshToken()
    if (!refreshToken) return false

    try {
      const res = await fetch(`${API_BASE}${API_PREFIX}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (!res.ok) {
        clearSession()
        return false
      }
      setSession((await res.json()) as TokenPair)
      return true
    } catch {
      // Network failure, not a rejected token: keep the stored refresh token so
      // a later attempt can still recover the session.
      return false
    } finally {
      inFlight = null
    }
  })()

  return inFlight
}

export async function endSession(): Promise<void> {
  const refreshToken = getRefreshToken()
  clearSession()
  if (!refreshToken) return
  try {
    // Best effort: revoke server-side so the token cannot be replayed. The
    // local session is already gone either way.
    await fetch(`${API_BASE}${API_PREFIX}/auth/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  } catch {
    /* ignore */
  }
}
