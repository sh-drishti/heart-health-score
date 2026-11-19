import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchPatients, fetchDashboard } from '@/api/client'
import type { DashboardBundle, Source } from '@/types'
import { PatientDirectory } from '@/components/PatientDirectory'
import { PatientReport, Section } from '@/components/PatientReport'
import { ClinicalValidation } from '@/components/ClinicalValidation'
import { ClinicalNotes } from '@/components/ClinicalNotes'
import { AppHeader } from '@/components/AppHeader'
import { Loader2 } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const SOURCE_LABEL: Record<Source, string> = {
  csv: 'CSV (internal)',
  payload: 'MongoDB payload',
}

export function DashboardPage() {
  // Source and patient live in the URL so the intake page can deep-link a
  // freshly saved encounter.
  const [params, setParams] = useSearchParams()
  const source = (params.get('source') === 'payload' ? 'payload' : 'csv') as Source
  const requested = params.get('patient') ?? ''

  const [ids, setIds] = useState<string[]>([])
  const [selectedPatient, setSelectedPatient] = useState('')
  const [bundle, setBundle] = useState<DashboardBundle | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const setSource = (next: Source) => {
    const p = new URLSearchParams(params)
    p.set('source', next)
    p.delete('patient')
    setParams(p)
  }

  useEffect(() => {
    setErr(null)
    fetchPatients(source)
      .then((list) => {
        setIds(list)
        setSelectedPatient((prev) => {
          if (requested && list.includes(requested)) return requested
          if (prev && list.includes(prev)) return prev
          return list[0] ?? ''
        })
      })
      .catch((e) => setErr(String(e)))
  }, [source, requested])

  useEffect(() => {
    if (!selectedPatient) {
      setBundle(null)
      return
    }
    setLoading(true)
    setErr(null)
    fetchDashboard(selectedPatient, source)
      .then(setBundle)
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false))
  }, [selectedPatient, source])

  return (
    <div className="min-h-screen bg-background">
      <AppHeader
        right={
          <Select value={source} onValueChange={(v) => setSource(v as Source)}>
            <SelectTrigger className="w-44" aria-label="Data source">
              <SelectValue>{(v: Source) => SOURCE_LABEL[v]}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="csv">{SOURCE_LABEL.csv}</SelectItem>
              <SelectItem value="payload">{SOURCE_LABEL.payload}</SelectItem>
            </SelectContent>
          </Select>
        }
      />

      <div className="flex flex-col lg:flex-row items-start">
        <aside className="w-full lg:w-64 shrink-0 bg-card border-b lg:border-b-0 lg:border-r max-h-72 lg:max-h-none lg:sticky lg:top-(--header-h) lg:h-[calc(100vh-var(--header-h))]">
          <PatientDirectory
            patientIds={ids}
            selectedPatient={selectedPatient}
            onSelect={setSelectedPatient}
          />
        </aside>

        <main className="flex-1 min-w-0 w-full px-6 py-5 pb-24">
          {err && (
            <div className="mb-4 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              {err}
            </div>
          )}
          {loading && (
            <div className="mb-4 inline-flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading dashboard…
            </div>
          )}

          {bundle && (
            <PatientReport bundle={bundle}>
              <Section title="Clinical Validation">
                <ClinicalValidation
                  patientId={String(bundle.patient.Patient_ID)}
                  assessment={bundle.assessment}
                />
              </Section>
            </PatientReport>
          )}
        </main>
      </div>

      {bundle && (
        <ClinicalNotes
          patientId={String(bundle.patient.Patient_ID)}
          initialNote={bundle.clinician_note ?? ''}
        />
      )}
    </div>
  )
}
