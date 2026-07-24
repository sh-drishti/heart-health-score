import type { DashboardBundle } from '@/types'
import { SEVERITY_HEX, type SeverityLevel } from '@/config/domains'
import { SeverityBadge } from './SeverityBadge'
import { Card, CardContent } from '@/components/ui/card'

function categoryLevel(category: string): SeverityLevel {
  const c = category.toLowerCase()
  if (c.includes('high') || c.includes('risk')) return 'risk'
  if (c.includes('border')) return 'warn'
  if (c.includes('health')) return 'ok'
  return 'neutral'
}

export function PatientHeader({ bundle }: { bundle: DashboardBundle }) {
  const { patient, assessment } = bundle
  const sex = patient.biological_sex === 'Male' ? 'Male' : 'Female'
  const level = categoryLevel(assessment.category ?? '')
  const score = Math.max(0, Math.min(100, assessment.hhs))
  const barColor = SEVERITY_HEX[level === 'neutral' ? 'ok' : level]

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-x-10 gap-y-4 py-4">
        <div>
          <div className="text-xs text-muted-foreground">Patient</div>
          <div className="text-xl font-semibold tracking-tight mt-0.5">
            {String(patient.Patient_ID ?? '')}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {String(patient.age ?? '')} yrs · {sex}
          </div>
        </div>

        <div className="h-10 w-px bg-border hidden sm:block" />

        <div className="min-w-56 flex-1">
          <div className="flex items-baseline justify-between gap-3">
            <div className="text-xs text-muted-foreground">Healthy Heart Score</div>
            <SeverityBadge level={level} label={assessment.category || 'N/A'} />
          </div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-3xl font-bold tracking-tight tabular-nums">
              {assessment.hhs}
            </span>
            <span className="text-sm text-muted-foreground">/ 100</span>
          </div>
          <div className="h-1.5 mt-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${score}%`, background: barColor }}
            />
          </div>
        </div>

        <div className="h-10 w-px bg-border hidden sm:block" />

        <div>
          <div className="text-xs text-muted-foreground">Data Confidence</div>
          <div className="text-xl font-semibold tabular-nums mt-0.5">
            {assessment.data_confidence}%
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {assessment.confidence_label}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
