import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@/auth/AuthContext'
import { ApiError } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ThemeToggle } from '@/components/ThemeToggle'
import { APP_NAME, Brand } from '@/components/Brand'
import { landingFor } from '@/auth/workspaces'

export function LoginPage() {
  const { user, loading, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  // Already signed in: go where they were headed, or to their role's home.
  if (!loading && user !== null) {
    const from = (location.state as { from?: string } | null)?.from
    return <Navigate to={landingFor(user.role, from)} replace />
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setErr(null)
    try {
      const signedIn = await signIn(email, password)
      const from = (location.state as { from?: string } | null)?.from
      navigate(landingFor(signedIn.role, from), { replace: true })
    } catch (e) {
      // 401 is a wrong email or password; anything else is the service failing,
      // and saying so avoids sending people to reset a password that is fine.
      setErr(
        e instanceof ApiError && e.status === 401
          ? 'Incorrect email or password.'
          : `Could not sign in: ${e instanceof Error ? e.message : String(e)}`,
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b bg-card/80 backdrop-blur">
        <div className="max-w-[1100px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <Link to="/" className="min-w-0" aria-label={`${APP_NAME} home`}>
            <Brand />
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <h2 className="page-title">Sign in</h2>
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
            Assessing your own heart health?{' '}
            <Link to="/register" className="font-medium text-primary hover:underline">
              Create an account
            </Link>
            . Clinician and staff accounts are issued by an administrator.
          </p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
                required
                autoFocus
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>

            {err && (
              <p className="text-sm text-destructive leading-snug" role="alert">
                {err}
              </p>
            )}

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Signing in…
                </>
              ) : (
                'Sign in'
              )}
            </Button>
          </form>

          <p className="text-xs text-muted-foreground mt-8 leading-relaxed border-t pt-4">
            Cardiovascular risk assessment on the HHS-v1.2 engine. Research
            prototype — not validated for clinical decision-making.
          </p>
        </div>
      </main>
    </div>
  )
}
