import { useEffect, useState } from 'react'
import './App.css'
import { fetchPatients, fetchDashboard } from '@/api/client'
import type { DashboardBundle, Source } from '@/types'
import { PatientDirectory } from '@/components/PatientDirectory'
import { PatientHeader } from '@/components/PatientHeader'
import { AssessmentAlerts } from '@/components/AssessmentAlerts'
import { DomainSummary } from '@/components/DomainSummary'
import { AdditionalInfo } from '@/components/AdditionalInfo'
import { ClinicalValidation } from '@/components/ClinicalValidation'
import { ClinicalNotes } from '@/components/ClinicalNotes'
import { ParametersTab } from '@/components/ParametersTab'
import { ThemeToggle } from '@/components/ThemeToggle'
import { HeartPulse, Loader2 } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

function App() {
  const [source, setSource] = useState<Source>('csv')
  const [ids, setIds] = useState<string[]>([])
  const [selectedPatient, setSelectedPatient] = useState('')
  const [bundle, setBundle] = useState<DashboardBundle | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    setErr(null)
    fetchPatients(source)
      .then((list) => {
        setIds(list)
        setSelectedPatient(list[0] ?? '')
      })
      .catch((e) => setErr(String(e)))
  }, [source])

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
      <header className="border-b bg-card/80 backdrop-blur sticky top-0 z-20">
        <div className="max-w-[1600px] mx-auto px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <HeartPulse className="h-4.5 w-4.5" />
            </span>
            <div>
              <h1 className="text-base font-semibold tracking-tight leading-tight">
                Healthy Heart Score
              </h1>
              <p className="text-xs text-muted-foreground leading-tight">
                Clinical Dashboard
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Select value={source} onValueChange={(v) => setSource(v as Source)}>
              <SelectTrigger className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="csv">CSV (internal)</SelectItem>
                <SelectItem value="payload">MongoDB payload</SelectItem>
              </SelectContent>
            </Select>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <div className="flex flex-col lg:flex-row items-start">
        <aside className="w-full lg:w-64 shrink-0 bg-card border-b lg:border-b-0 lg:border-r max-h-72 lg:max-h-none lg:sticky lg:top-[61px] lg:h-[calc(100vh-61px)]">
          <PatientDirectory
            patientIds={ids}
            selectedPatient={selectedPatient}
            onSelect={setSelectedPatient}
          />
        </aside>

        <main className="flex-1 min-w-0 w-full max-w-[1200px] mx-auto px-6 py-5">
          {err && (
            <div className="mb-4 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              {err}
            </div>
          )}
          {loading && (
            <div className="mb-4 inline-flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading dashboard…
            </div>
          )}

          {bundle && (
            <>
              <div className="sticky top-[69px] lg:top-[69px] z-10 -mx-2 px-2 py-2 bg-background/90 backdrop-blur">
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
                  <ClinicalValidation
                    patientId={String(bundle.patient.Patient_ID)}
                    assessment={bundle.assessment}
                  />
                </TabsContent>

                <TabsContent value="parameters" className="mt-4">
                  <ParametersTab
                    patientData={bundle.patient_data}
                    assessment={bundle.assessment}
                  />
                </TabsContent>
              </Tabs>
            </>
          )}
        </main>

        {bundle && (
          <aside className="w-full lg:w-80 shrink-0 px-6 lg:px-0 lg:pr-5 pb-5 lg:pb-0 lg:py-5 lg:sticky lg:top-[61px]">
            <ClinicalNotes
              patientId={String(bundle.patient.Patient_ID)}
              initialNote={bundle.clinician_note ?? ''}
            />
          </aside>
        )}
      </div>
    </div>
  )
}

export default App
