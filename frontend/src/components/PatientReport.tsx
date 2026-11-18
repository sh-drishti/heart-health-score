import type { ReactNode } from 'react'
import type { DashboardBundle, MonitoringData } from '@/types'
import { ScoreCard } from './ScoreCard'
import { DomainSummary } from './DomainSummary'
import { AllParametersSheet } from './AllParametersSheet'
import { TrendsSection } from './TrendsSection'
import { AdditionalInfo } from './AdditionalInfo'

/** A titled block of the report. The title is the dashboard's main heading style. */
export function Section({
  title,
  actions,
  children,
}: {
  title: string
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h2 className="section-title">{title}</h2>
        {actions}
      </div>
      {children}
    </section>
  )
}

interface Props {
  bundle: DashboardBundle
  /** Passed through to the trend charts; see TrendsSection. */
  loadMonitoring?: (patientId: string) => Promise<MonitoringData | null>
  /** Further sections after the shared ones, e.g. clinical validation. */
  children?: ReactNode
}

/**
 * One patient's report: the sections run the full width of the centre and the
 * score card stays pinned on the right. Below xl there is no room for a third
 * column, so the score card moves above the sections instead.
 *
 * Shared by the clinician dashboard and a patient's own page; each page adds
 * its own sections as children.
 */
export function PatientReport({ bundle, loadMonitoring, children }: Props) {
  const patientId = String(bundle.patient.Patient_ID)

  return (
    <div className="flex flex-col xl:flex-row gap-6 items-start">
      <div className="order-2 xl:order-1 flex-1 min-w-0 w-full space-y-8">
        <Section title="Domain Summary">
          <DomainSummary
            patientData={bundle.patient_data}
            assessment={bundle.assessment}
            actions={<AllParametersSheet patientData={bundle.patient_data} />}
          />
        </Section>

        <Section title="Trends">
          <TrendsSection
            patientId={patientId}
            assessment={bundle.assessment}
            loadMonitoring={loadMonitoring}
          />
        </Section>

        <Section title="Additional Clinical Information">
          <AdditionalInfo patient={bundle.patient} />
        </Section>

        {children}
      </div>

      {/* Sticky under the 61px header, and short enough at the bottom to
          clear the notes bubble. */}
      <aside className="order-1 xl:order-2 w-full xl:w-80 shrink-0 xl:sticky xl:top-[77px] xl:max-h-[calc(100vh-77px-5.5rem)] xl:overflow-y-auto">
        <ScoreCard bundle={bundle} />
      </aside>
    </div>
  )
}
