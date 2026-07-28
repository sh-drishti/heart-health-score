import type { Assessment } from '@/types'
import { AlertTriangle, Info, ShieldAlert } from 'lucide-react'

// Surfaces scorer output that was previously dropped by the UI:
// red flags, abstention state + reasons, and scorer notes.
export function AssessmentAlerts({ assessment }: { assessment: Assessment }) {
  const notes = Array.isArray(assessment.notes)
    ? assessment.notes
    : assessment.notes
      ? [assessment.notes]
      : []

  const hasFlags = assessment.red_flags.length > 0
  if (!hasFlags && !assessment.abstained && notes.length === 0) return null

  return (
    <div className="space-y-2.5">
      {hasFlags && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-rose-700 dark:text-rose-400 mb-1.5">
            <AlertTriangle className="h-4 w-4" />
            Critical Red Flags ({assessment.red_flags.length})
          </div>
          <ul className="space-y-1 text-sm text-rose-700/90 dark:text-rose-300/90 list-disc pl-6">
            {assessment.red_flags.map((flag) => (
              <li key={flag.flag}>{flag.message}</li>
            ))}
          </ul>
        </div>
      )}

      {assessment.abstained && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-700 dark:text-amber-400 mb-1.5">
            <ShieldAlert className="h-4 w-4" />
            Scorer Abstained
          </div>
          <ul className="space-y-1 text-sm text-amber-700/90 dark:text-amber-300/90 list-disc pl-6">
            {assessment.abstention_reasons.map((reason, i) => (
              <li key={i}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      {notes.length > 0 && (
        <div className="rounded-xl border bg-card shadow-xs px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground mb-1.5">
            <Info className="h-4 w-4" />
            Scorer Notes
          </div>
          <ul className="space-y-1 text-sm text-muted-foreground list-disc pl-6">
            {notes.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
