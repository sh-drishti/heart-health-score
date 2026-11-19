import { useState } from 'react'
import type { DashboardBundle } from '@/types'
import { SEVERITY_HEX, type SeverityLevel } from '@/config/domains'
import { SeverityBadge } from './SeverityBadge'
import { AlertTriangle, ChevronDown, Info, ShieldAlert } from 'lucide-react'
import { cn } from '@/lib/utils'

function categoryLevel(category: string): SeverityLevel {
  const c = category.toLowerCase()
  if (c.includes('high') || c.includes('risk')) return 'risk'
  if (c.includes('border') || c.includes('moderate') || c.includes('mildly')) return 'warn'
  if (c.includes('favorable') || c.includes('health')) return 'ok'
  return 'neutral'
}

/**
 * The score at a glance, pinned beside the report. It also carries what used
 * to sit in front of the report as banners: red flags, an abstention, and the
 * scorer's notes. They stay one glance away without pushing the content down.
 */
export function ScoreCard({ bundle }: { bundle: DashboardBundle }) {
  const { patient, assessment } = bundle
  const [notesOpen, setNotesOpen] = useState(false)

  const sex = patient.biological_sex === 'Male' ? 'Male' : patient.biological_sex === 'Female' ? 'Female' : String(patient.biological_sex ?? '')
  const level = categoryLevel(assessment.category ?? '')
  const score = Math.max(0, Math.min(100, assessment.hhs))
  const confidence = Math.max(0, Math.min(100, assessment.data_confidence))
  const visitDate = typeof bundle.visit?.visit_date === 'string' ? bundle.visit.visit_date : null

  const notes = Array.isArray(assessment.notes)
    ? assessment.notes
    : assessment.notes
      ? [assessment.notes]
      : []
  const flags = assessment.red_flags

  return (
    <div className="rounded-lg border bg-card shadow-xs divide-y">
      <div className="p-4">
        <div className="text-xs text-muted-foreground">Patient</div>
        <div className="card-title mt-0.5 break-all">{String(patient.Patient_ID ?? '')}</div>
        <div className="text-xs text-muted-foreground mt-0.5">
          {String(patient.age ?? '')} yrs · {sex}
          {visitDate && <> · visit {visitDate}</>}
        </div>
      </div>

      <div className="p-4">
        <div className="text-xs text-muted-foreground">Heart Health Score</div>
        <div className="flex items-baseline gap-1.5 mt-1">
          <span className="font-heading text-4xl font-bold tabular-nums">{assessment.hhs}</span>
          <span className="text-sm text-muted-foreground">/ 100</span>
        </div>
        <div className="h-1.5 mt-3 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{ width: `${score}%`, background: SEVERITY_HEX[level === 'neutral' ? 'ok' : level] }}
          />
        </div>
        <div className="mt-3">
          <SeverityBadge level={level} label={assessment.category || 'N/A'} />
        </div>
      </div>

      <div className="p-4">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-xs text-muted-foreground">Data confidence</span>
          <span className="text-xs text-muted-foreground">{assessment.confidence_label}</span>
        </div>
        <div className="font-heading text-2xl font-semibold tabular-nums mt-0.5">
          {assessment.data_confidence}%
        </div>
        <div className="h-1 mt-2 rounded-full bg-muted overflow-hidden">
          <div className="h-full rounded-full bg-primary/60" style={{ width: `${confidence}%` }} />
        </div>
      </div>

      {assessment.abstained && (
        <div className="p-4 bg-amber-500/5">
          <div className="flex items-center gap-1.5 text-sm font-semibold text-amber-700 dark:text-amber-400">
            <ShieldAlert className="h-4 w-4" />
            Score is provisional
          </div>
          <ul className="mt-1.5 space-y-1 text-xs text-amber-800/90 dark:text-amber-300/90 list-disc pl-5">
            {assessment.abstention_reasons.map((reason, i) => (
              <li key={i}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="p-4">
        <div
          className={cn(
            'flex items-center gap-1.5 text-sm font-semibold',
            flags.length > 0 ? 'text-rose-700 dark:text-rose-400' : 'text-muted-foreground',
          )}
        >
          <AlertTriangle className="h-4 w-4" />
          Red flags ({flags.length})
        </div>
        {flags.length === 0 ? (
          <p className="text-xs text-muted-foreground mt-1">None detected.</p>
        ) : (
          <ul className="mt-2 space-y-1.5">
            {flags.map((flag) => (
              <li
                key={flag.flag}
                className="rounded-md border border-rose-500/25 bg-rose-500/5 px-2.5 py-1.5 text-xs leading-snug text-rose-800 dark:text-rose-300"
              >
                {flag.message}
              </li>
            ))}
          </ul>
        )}
      </div>

      {notes.length > 0 && (
        <div className="px-4 py-3">
          <button
            type="button"
            onClick={() => setNotesOpen((o) => !o)}
            aria-expanded={notesOpen}
            className="flex w-full items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer"
          >
            <Info className="h-3.5 w-3.5" />
            Scorer notes ({notes.length})
            <ChevronDown
              className={cn('ml-auto h-3.5 w-3.5 transition-transform', notesOpen && 'rotate-180')}
            />
          </button>
          {notesOpen && (
            <ul className="mt-2 space-y-1 text-xs text-muted-foreground list-disc pl-5">
              {notes.map((note, i) => (
                <li key={i}>{note}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
