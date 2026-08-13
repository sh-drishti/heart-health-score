import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import * as api from '@/api/client'
import { getUser, refreshSession, subscribe } from '@/api/session'
import type { AuthUser } from '@/types'

interface AuthState {
  user: AuthUser | null
  /** True until the stored session has been checked, so guards do not flash. */
  loading: boolean
  signIn: (email: string, password: string) => Promise<AuthUser>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(getUser)
  const [loading, setLoading] = useState(true)

  // The session store is the source of truth: a background refresh or a 401
  // that clears the session has to move this state too.
  useEffect(() => subscribe(setUser), [])

  useEffect(() => {
    // Only the refresh token survives a reload, so restoring a session means
    // redeeming it for a fresh access token.
    let cancelled = false
    refreshSession().finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    // setSession inside login() notifies the subscriber above.
    return api.login(email, password)
  }, [])

  const signOut = useCallback(async () => {
    await api.logout()
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return context
}
