import { Link, Navigate, useLocation } from 'react-router-dom'
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

/** Where a role belongs, so this screen can offer a way out rather than a dead end. */
const HOME: Record<Role, string> = {
  clinician: '/dashboard',
  staff: '/entry',
  patient: '/my-health',
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
              That view is for clinical staff reviewing other people's records.
              Yours is under My Heart Health.
            </>
          ) : (
            <>
              You are signed in as <span className="font-medium">{role}</span>,
              which does not have access to this view.
            </>
          )}
        </p>
        <div className="mt-5 flex flex-col items-center gap-2">
          <Link
            to={HOME[role]}
            className="text-sm font-medium text-primary hover:underline underline-offset-2"
          >
            Go to my workspace
          </Link>
          <button
            onClick={signOut}
            className="text-sm text-muted-foreground hover:underline underline-offset-2"
          >
            Sign in as a different user
          </button>
        </div>
      </div>
    </div>
  )
}
