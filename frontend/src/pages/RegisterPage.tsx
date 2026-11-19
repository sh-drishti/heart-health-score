import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@/auth/AuthContext'
import { ApiError, register } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ThemeToggle } from '@/components/ThemeToggle'
import { APP_NAME, Brand } from '@/components/Brand'

/**
 * Open sign-up, for someone assessing their own heart health.
 *
 * Only creates patient accounts — role and patient id are decided server-side.
 * Clinician and staff accounts are issued by an administrator.
 */
export function RegisterPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  if (!loading && user !== null) {
    return <Navigate to={user.role === 'patient' ? '/my-health' : '/'} replace />
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setErr(null)
    try {
      await register(email, password, name)
      // Registering signs you in, so go straight to entering a first encounter.
      navigate('/entry', { replace: true })
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setErr('An account already exists for that email. Sign in instead.')
      } else if (e instanceof ApiError && e.status === 422) {
        setErr(
          typeof e.detail === 'string'
            ? e.detail
            : 'Check the email address and use at least 8 characters for the password.',
        )
      } else {
        setErr(`Could not create the account: ${e instanceof Error ? e.message : String(e)}`)
      }
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
          <h2 className="page-title">Create your account</h2>
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
            Record what you know about your heart health and get a score. Fill in
            as much or as little as you have — the score reports how confident it
            is in the data you gave it.
          </p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="name">Your name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                required
                autoFocus
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                minLength={8}
                required
              />
              <p className="text-xs text-muted-foreground">At least 8 characters.</p>
            </div>

            {err && (
              <p className="text-sm text-destructive leading-snug" role="alert">
                {err}
              </p>
            )}

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Creating account…
                </>
              ) : (
                'Create account'
              )}
            </Button>

            <p className="text-sm text-muted-foreground text-center">
              Already have one?{' '}
              <Link to="/login" className="font-medium text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </form>

          <p className="text-xs text-muted-foreground mt-8 leading-relaxed">
            Research prototype — not validated for clinical decision-making. It
            does not replace advice from a doctor.
          </p>
        </div>
      </main>
    </div>
  )
}
