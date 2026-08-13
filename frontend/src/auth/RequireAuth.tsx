import { Navigate, useLocation } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from './AuthContext'
import type { Role } from '@/types'

/**
 * Route guard. Sends unauthenticated visitors to /login, and signed-in users
 * without one of `roles` to an explanation rather than a redirect loop.
 *
 * This is a usability boundary, not the security boundary — the API enforces
 * the same rules, so a hand-edited URL gains nothing.
 */
export function RequireAuth({
  roles,
  children,
}: {
  roles: Role[]
  children: React.ReactNode
}) {
  const { user, loading } = useAuth()
  const location = useLocation()

  // A stored refresh token is still being redeemed; redirecting now would sign
  // out anyone who reloads the page.
  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (user === null) {
    // `from` lets the login page return the user where they were headed.
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (!roles.includes(user.role)) {
    return <WrongRole role={user.role} />
  }

  return <>{children}</>
}

function WrongRole({ role }: { role: Role }) {
  const { signOut } = useAuth()

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-6">
      <div className="max-w-md text-center">
        <h1 className="text-lg font-semibold tracking-tight">
          This workspace is not available to your account
        </h1>
        <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
          {role === 'patient' ? (
            <>
              Patient accounts do not have a web view yet — your Heart Health
              Score and trends are in the mobile app.
            </>
          ) : (
            <>
              You are signed in as <span className="font-medium">{role}</span>,
              which does not have access to this view.
            </>
          )}
        </p>
        <button
          onClick={signOut}
          className="mt-5 text-sm font-medium text-primary hover:underline underline-offset-2"
        >
          Sign in as a different user
        </button>
      </div>
    </div>
  )
}
