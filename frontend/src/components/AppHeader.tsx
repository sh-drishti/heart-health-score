import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import { workspacesFor, type Workspace } from '@/auth/workspaces'
import { cn } from '@/lib/utils'
import { APP_NAME, Brand } from './Brand'
import { ThemeToggle } from './ThemeToggle'
import { UserMenu } from './UserMenu'

interface Props {
  /** Page-specific controls before the theme toggle, e.g. the data source. */
  right?: ReactNode
}

function WorkspaceNav({ workspaces, compact }: { workspaces: Workspace[]; compact?: boolean }) {
  return (
    <nav
      aria-label="Workspaces"
      className="inline-flex items-center gap-1 rounded-lg bg-muted/70 p-1"
    >
      {workspaces.map((w) => (
        <NavLink
          key={w.to}
          to={w.to}
          className={({ isActive }) =>
            cn(
              'inline-flex shrink-0 items-center gap-1.5 rounded-md font-medium transition-colors',
              compact ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-sm',
              isActive
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:text-foreground hover:bg-background/70',
            )
          }
        >
          <w.icon className={compact ? 'h-3.5 w-3.5' : 'h-4 w-4'} />
          {w.label}
        </NavLink>
      ))}
    </nav>
  )
}

/**
 * Brand on the left, the workspaces the signed-in role can open in the centre
 * (so nothing is shown greyed out), and page controls, the theme toggle and
 * sign-out on the right. The brand goes to `/`, which lands on the role's home.
 *
 * Below xl there is no room for all three in one row, so the nav drops to a
 * second row. The two rows' heights are fixed and match `--header-h` in
 * App.css, which sticky panels use to sit just below the header.
 */
export function AppHeader({ right }: Props) {
  const { user } = useAuth()
  const workspaces = user ? workspacesFor(user.role) : []
  const showNav = workspaces.length > 1

  return (
    <header className="border-b bg-card sticky top-0 z-20">
      <div className="px-4 sm:px-6 h-16 grid grid-cols-[1fr_auto] xl:grid-cols-[1fr_auto_1fr] items-center gap-4">
        <Link to="/" aria-label={`${APP_NAME} home`} className="min-w-0 justify-self-start">
          <Brand />
        </Link>

        {showNav && (
          <div className="hidden xl:block">
            <WorkspaceNav workspaces={workspaces} />
          </div>
        )}

        <div className="flex items-center gap-2 justify-self-end">
          {right}
          <ThemeToggle />
          <UserMenu />
        </div>
      </div>

      {showNav && (
        <div className="xl:hidden h-10 flex items-start overflow-x-auto px-4 sm:px-6">
          <WorkspaceNav workspaces={workspaces} compact />
        </div>
      )}
    </header>
  )
}
