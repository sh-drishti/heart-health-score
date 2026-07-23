import type { SeverityLevel } from '@/config/domains'
import { SEVERITY_UI } from '@/config/domains'
import { cn } from '@/lib/utils'

interface Props {
  level: SeverityLevel
  label: string
  className?: string
}

export function SeverityBadge({ level, label, className }: Props) {
  const ui = SEVERITY_UI[level]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold',
        ui.badge,
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', ui.dot)} />
      {label}
    </span>
  )
}

export function SeverityDot({ level, className }: { level: SeverityLevel; className?: string }) {
  return (
    <span className={cn('inline-block h-2 w-2 rounded-full', SEVERITY_UI[level].dot, className)} />
  )
}
