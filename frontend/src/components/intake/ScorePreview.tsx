import type { Assessment } from '@/types'
import { SEVERITY_HEX, type SeverityLevel } from '@/config/domains'
import { SeverityBadge } from '../SeverityBadge'
import { AlertTriangle, Loader2, ShieldAlert } from 'lucide-react'

function bandLevel(score: number): SeverityLevel {
  if (score >= 80) return 'ok'
  if (score >= 50) return 'warn'
  return 'risk'
}

interface Props {
  assessment: Assessment | null
  scoring: boolean
  error: string | null
}

// Live scoring panel. The Streamlit intake app computed the assessment on every
// rerun but never displayed it — this surfaces it so entry errors are visible
// before the encounter is written.
export function ScorePreview({ assessment, scoring, error }: Props) {
  if (error) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
        {error}
      </div>
    )
  }

  if (!assessment) {
    return (
      <div className="rounded-xl border bg-card px-4 py-6 text-sm text-muted-foreground text-center">
        {scoring ? (
          <span className="inline-flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" /> Scoring…
          </span>
        ) : (
          'Enter values to see the live score.'
        )}
      </div>
    )
  }

  const level = bandLevel(assessment.hhs)
  const interval = assessment.score_interval
  const suppressed = assessment.red_flags.some((f) => f.suppress_score)

  return (
    <div className="rounded-xl border bg-card shadow-xs overflow-hidden">
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Live Assessment
        </span>
        {scoring && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
      </div>

      <div className="p-4 space-y-4">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold tracking-tight tabular-nums">
              {assessment.hhs}
            </span>
            <span className="text-sm text-muted-foreground">/ 100</span>
          </div>
          <div className="h-1.5 mt-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.max(0, Math.min(100, assessment.hhs))}%`,
                background: SEVERITY_HEX[level],
              }}
            />
          </div>
          <p className="text-xs text-muted-foreground mt-2 leading-snug">
            {assessment.category}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <div className="text-xs text-muted-foreground">Confidence</div>
            <div className="font-semibold tabular-nums">
              {assessment.data_confidence}%
            </div>
            <div className="text-xs text-muted-foreground">
              {assessment.confidence_label}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Burden</div>
            <div className="font-semibold tabular-nums">
              {assessment.burden.total}
            </div>
            <div className="text-xs text-muted-foreground">
              main {assessment.burden.main}
            </div>
          </div>
        </div>

        {interval && (
          <div>
            <div className="text-xs text-muted-foreground mb-1">
              Score interval (floor → optimistic)
            </div>
            <div className="text-sm tabular-nums">
              {interval.floor} → {interval.expected} → {interval.optimistic}
              <span className="text-xs text-muted-foreground ml-2">
                W {interval.optimistic_to_expected_width_W}
              </span>
            </div>
          </div>
        )}

        {(assessment.abstained || suppressed) && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-700 dark:text-amber-400 mb-1">
              <ShieldAlert className="h-3.5 w-3.5" />
              {suppressed ? 'Score interpretation suppressed' : 'Scorer abstained'}
            </div>
            <ul className="text-xs text-amber-700/90 dark:text-amber-300/90 space-y-0.5 list-disc pl-4">
              {assessment.abstention_reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
        )}

        {assessment.red_flags.length > 0 && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/5 px-3 py-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-700 dark:text-rose-400 mb-1">
              <AlertTriangle className="h-3.5 w-3.5" />
              Red flags ({assessment.red_flags.length})
            </div>
            <ul className="text-xs text-rose-700/90 dark:text-rose-300/90 space-y-0.5 list-disc pl-4">
              {assessment.red_flags.map((f) => (
                <li key={f.flag}>{f.message}</li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <div className="text-xs text-muted-foreground mb-1.5">Domain severities</div>
          <div className="space-y-1">
            {assessment.domain_rows.slice(0, 5).map((row) => (
              <div key={row.Domain} className="flex items-center justify-between gap-2 text-xs">
                <span className="truncate">{row.Domain}</span>
                <span className="flex items-center gap-2 shrink-0">
                  <span className="tabular-nums text-muted-foreground">
                    {row['Total domain contribution'].toFixed(2)} pts
                  </span>
                  <SeverityBadge
                    level={
                      row.Severity >= 0.67 ? 'risk' : row.Severity >= 0.33 ? 'warn' : 'ok'
                    }
                    label={row.Status}
                  />
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
