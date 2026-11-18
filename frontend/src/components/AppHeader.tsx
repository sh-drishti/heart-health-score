import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { HeartPulse } from 'lucide-react'
import { useAuth } from '@/auth/AuthContext'
import { workspacesFor } from '@/auth/workspaces'
import { cn } from '@/lib/utils'
import { ThemeToggle } from './ThemeToggle'
import { UserMenu } from './UserMenu'

interface Props {
  /** Names the role-specific view, e.g. "Clinical Dashboard" or "Data Entry". */
  subtitle: string
  right?: ReactNode
}

/**
 * Lists only the workspaces the signed-in role can open, so nothing is shown
 * greyed out. A role with a single workspace gets no nav at all. The logo goes
 * to `/`, which lands on the role's home.
 */
export function AppHeader({ subtitle, right }: Props) {
  const { user } = useAuth()
  const workspaces = user ? workspacesFor(user.role) : []

  return (
    <header className="border-b bg-card/80 backdrop-blur sticky top-0 z-20">
      <div className="px-6 h-[61px] flex items-center justify-between gap-4">
        <div className="flex items-center gap-6 min-w-0">
          <Link to="/" className="flex items-center gap-2.5 min-w-0 group">
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground shrink-0">
              <HeartPulse className="h-4.5 w-4.5" />
            </span>
            <div className="min-w-0 hidden sm:block">
              <h1 className="font-heading text-base font-bold leading-tight truncate group-hover:underline underline-offset-2">
                Healthy Heart Score
              </h1>
              <p className="text-xs text-muted-foreground leading-tight truncate">
                {subtitle}
              </p>
            </div>
          </Link>

          {workspaces.length > 1 && (
            <nav aria-label="Workspaces" className="hidden md:flex items-center gap-1">
              {workspaces.map((w) => (
                <NavLink
                  key={w.to}
                  to={w.to}
                  className={({ isActive }) =>
                    cn(
                      'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted',
                    )
                  }
                >
                  <w.icon className="h-4 w-4" />
                  {w.label}
                </NavLink>
              ))}
            </nav>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {right}
          <UserMenu />
          <ThemeToggle />
        </div>
      </div>

      {workspaces.length > 1 && (
        <nav
          aria-label="Workspaces"
          className="md:hidden flex items-center gap-1 overflow-x-auto px-4 pb-2 -mt-1"
        >
          {workspaces.map((w) => (
            <NavLink
              key={w.to}
              to={w.to}
              className={({ isActive }) =>
                cn(
                  'inline-flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium',
                  isActive ? 'bg-primary/10 text-primary' : 'text-muted-foreground',
                )
              }
            >
              <w.icon className="h-3.5 w-3.5" />
              {w.label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  )
}
