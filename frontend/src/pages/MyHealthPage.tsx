import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardPlus, Loader2, StickyNote } from 'lucide-react'
import { fetchMyDashboard, fetchMyMonitoring, fetchMyNote } from '@/api/client'
import { ApiError } from '@/api/client'
import type { DashboardBundle, SavedNote } from '@/types'
import { AppHeader } from '@/components/AppHeader'
import { PatientHeader } from '@/components/PatientHeader'
import { AssessmentAlerts } from '@/components/AssessmentAlerts'
import { DomainSummary } from '@/components/DomainSummary'
import { AdditionalInfo } from '@/components/AdditionalInfo'
import { ParametersTab } from '@/components/ParametersTab'
import { buttonVariants } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'

/**
 * A patient's own dashboard: the same components the clinical dashboard uses,
 * against /me/* instead of a patient id.
 *
 * Deliberately not a mode on DashboardPage — that page owns patient selection,
 * the CSV/MongoDB source switch and the clinician validation panel, none of
 * which apply here. The shared surface is the tabs, not the page shell.
 */
export function MyHealthPage() {
  const [bundle, setBundle] = useState<DashboardBundle | null>(null)
  const [note, setNote] = useState<SavedNote | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [noAssessment, setNoAssessment] = useState(false)

  // ParametersTab takes the loader rather than assuming the clinician route.
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
      <AppHeader
        subtitle="My Heart Health"
        right={
          <Link
            to="/entry"
            className={buttonVariants({ size: 'sm', variant: 'outline' })}
          >
            <ClipboardPlus className="h-4 w-4" />
            Record a visit
          </Link>
        }
      />

      <main className="max-w-[1200px] mx-auto px-6 py-5">
        {loading && (
          <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading your score…
          </div>
        )}

        {err && (
          <div className="mb-4 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {err}
          </div>
        )}

        {noAssessment && (
          <div className="rounded-2xl border bg-card p-8 text-center max-w-lg mx-auto mt-8">
            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary mb-4">
              <ClipboardPlus className="h-6 w-6" />
            </span>
            <h2 className="text-lg font-semibold tracking-tight">
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
          <>
            <div className="sticky top-[69px] z-10 -mx-2 px-2 py-2 bg-background/90 backdrop-blur">
              <PatientHeader bundle={bundle} />
            </div>

            <div className="mt-4">
              <AssessmentAlerts assessment={bundle.assessment} />
            </div>

            <Tabs defaultValue="summary" className="mt-4">
              <TabsList>
                <TabsTrigger value="summary">Domain Summary</TabsTrigger>
                <TabsTrigger value="parameters">All Parameters</TabsTrigger>
              </TabsList>

              <TabsContent value="summary" className="mt-4">
                <DomainSummary
                  patientData={bundle.patient_data}
                  assessment={bundle.assessment}
                />
                <AdditionalInfo patient={bundle.patient} />
              </TabsContent>

              <TabsContent value="parameters" className="mt-4">
                <ParametersTab
                  patientId={String(bundle.patient.Patient_ID)}
                  patientData={bundle.patient_data}
                  assessment={bundle.assessment}
                  loadMonitoring={loadMonitoring}
                />
              </TabsContent>
            </Tabs>

            {note && <ClinicianNote note={note} />}
          </>
        )}
      </main>
    </div>
  )
}

/** Read-only: a review note is written by a clinician, never by the patient. */
function ClinicianNote({ note }: { note: SavedNote }) {
  return (
    <section className="mt-4 rounded-xl border bg-card shadow-xs overflow-hidden">
      <div className="p-3 border-b flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <StickyNote className="h-3.5 w-3.5" />
        Note from your clinician
      </div>
      <div className="p-4 space-y-2">
        <p className="text-sm whitespace-pre-wrap leading-relaxed">{note.note}</p>
        <p className="text-xs text-muted-foreground">
          {note.author ? `${note.author} · ` : ''}
          {new Date(note.updated_at).toLocaleString()}
        </p>
      </div>
    </section>
  )
}
