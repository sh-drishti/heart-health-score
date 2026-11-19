import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardPlus, Loader2, StickyNote } from 'lucide-react'
import { fetchMyDashboard, fetchMyMonitoring, fetchMyNote } from '@/api/client'
import { ApiError } from '@/api/client'
import type { DashboardBundle, SavedNote } from '@/types'
import { AppHeader } from '@/components/AppHeader'
import { PatientReport, Section } from '@/components/PatientReport'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

/**
 * A patient's own dashboard: the same components the clinical dashboard uses,
 * against /me/* instead of a patient id.
 *
 * Deliberately not a mode on DashboardPage — that page owns patient selection,
 * the CSV/MongoDB source switch, the clinician validation panel and the note
 * editor, none of which apply here. The shared surface is PatientReport.
 */
export function MyHealthPage() {
  const [bundle, setBundle] = useState<DashboardBundle | null>(null)
  const [note, setNote] = useState<SavedNote | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [noAssessment, setNoAssessment] = useState(false)

  // The trends take the loader rather than assuming the clinician route.
  // Stable identity, or its effect would refetch on every render.
  const loadMonitoring = useCallback(() => fetchMyMonitoring(), [])

  useEffect(() => {
    let stale = false
    setLoading(true)
    setErr(null)
    setNoAssessment(false)

    fetchMyDashboard()
      .then((data) => {
        if (!stale) setBundle(data)
      })
      .catch((e) => {
        if (stale) return
        // 404 is the expected first-run state, not a failure: the account
        // exists but no encounter has been recorded yet.
        if (e instanceof ApiError && e.status === 404) setNoAssessment(true)
        else setErr(String(e))
      })
      .finally(() => {
        if (!stale) setLoading(false)
      })

    // A note is written by a clinician, so most patients will not have one.
    fetchMyNote()
      .then((saved) => {
        if (!stale) setNote(saved)
      })
      .catch(() => {
        /* Not worth surfacing: the score is the point of this page. */
      })

    return () => {
      stale = true
    }
  }, [])

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />

      <main className="px-6 py-5 pb-12">
        {loading && (
          <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading your score…
          </div>
        )}

        {err && (
          <div className="mb-4 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {err}
          </div>
        )}

        {noAssessment && (
          <div className="rounded-lg border bg-card p-8 text-center max-w-lg mx-auto mt-8">
            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-md bg-primary/10 text-primary mb-4">
              <ClipboardPlus className="h-6 w-6" />
            </span>
            <h2 className="section-title">
              Nothing recorded yet
            </h2>
            <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
              Enter what you know about your health — age, blood pressure,
              cholesterol, whether you smoke — and you will get a Heart Health
              Score. Anything you leave out is reported as reduced confidence
              rather than guessed at.
            </p>
            <Link to="/entry" className={cn(buttonVariants(), 'mt-5')}>
              Record your first visit
            </Link>
          </div>
        )}

        {bundle && (
          <PatientReport bundle={bundle} loadMonitoring={loadMonitoring}>
            {note && (
              <Section title="Note from your clinician">
                <ClinicianNote note={note} />
              </Section>
            )}
          </PatientReport>
        )}
      </main>
    </div>
  )
}

/** Read-only: a review note is written by a clinician, never by the patient. */
function ClinicianNote({ note }: { note: SavedNote }) {
  return (
    <div className="rounded-lg border bg-card shadow-xs overflow-hidden">
      <div className="p-4 space-y-2">
        <StickyNote className="h-4 w-4 text-primary" />
        <p className="text-sm whitespace-pre-wrap leading-relaxed">{note.note}</p>
        <p className="text-xs text-muted-foreground">
          {note.author ? `${note.author} · ` : ''}
          {new Date(note.updated_at).toLocaleString()}
        </p>
      </div>
    </div>
  )
}
