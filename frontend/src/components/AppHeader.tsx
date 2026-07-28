import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { HeartPulse } from 'lucide-react'
import { ThemeToggle } from './ThemeToggle'

interface Props {
  /** Names the role-specific view, e.g. "Clinical Dashboard" or "Data Entry". */
  subtitle: string
  right?: ReactNode
}

// Deliberately carries no nav between /dashboard and /entry: the two views are
// for different roles. The logo goes to the chooser at /, not to the other view.
export function AppHeader({ subtitle, right }: Props) {
  return (
    <header className="border-b bg-card/80 backdrop-blur sticky top-0 z-20">
      <div className="max-w-[1600px] mx-auto px-6 py-3.5 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2.5 min-w-0 group">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shrink-0">
            <HeartPulse className="h-4.5 w-4.5" />
          </span>
          <div className="min-w-0">
            <h1 className="text-base font-semibold tracking-tight leading-tight truncate group-hover:underline underline-offset-2">
              Healthy Heart Score
            </h1>
            <p className="text-xs text-muted-foreground leading-tight truncate">
              {subtitle}
            </p>
          </div>
        </Link>

        <div className="flex items-center gap-2 shrink-0">
          {right}
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
