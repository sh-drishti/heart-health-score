import type { Patient } from '@/types'
import { SECTION_FIELDS, OPTIONAL_MARKER_UNITS, getBadge } from '@/config/domains'
import { SeverityBadge } from './SeverityBadge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertTriangle, CheckCircle2, HeartPulse, Minus } from 'lucide-react'

type Style = 'badge' | 'alert' | 'history' | 'value'

function InfoRow({
  label,
  value,
  style,
  column,
}: {
  label: string
  value: number | string | null
  style: Style
  column: string
}) {
  const { level, display } = getBadge(value)

  let right: React.ReactNode

  if (style === 'badge') {
    right = level ? (
      <SeverityBadge level={level} label={display} />
    ) : (
      <span className="text-sm">{display}</span>
    )
  } else if (style === 'alert') {
    right =
      display === 'Yes' ? (
        <span className="inline-flex items-center gap-1.5 text-sm font-medium text-rose-600 dark:text-rose-400">
          <AlertTriangle className="h-3.5 w-3.5" /> Present
        </span>
      ) : display === 'No' ? (
        <span className="inline-flex items-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="h-3.5 w-3.5" /> None
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
          <Minus className="h-3.5 w-3.5" /> Unknown
        </span>
      )
  } else if (style === 'history') {
    right =
      display === 'Yes' ? (
        <span className="inline-flex items-center gap-1.5 text-sm font-medium text-rose-600 dark:text-rose-400">
          <HeartPulse className="h-3.5 w-3.5" /> Present
        </span>
      ) : display === 'No' ? (
        <span className="text-sm text-muted-foreground">None</span>
      ) : (
        <span className="text-sm text-muted-foreground">Unknown</span>
      )
  } else {
    const unit = OPTIONAL_MARKER_UNITS[column] ?? ''
    right = (
      <span className="text-sm tabular-nums">
        {display === 'Missing' ? (
          <span className="text-muted-foreground">{display}</span>
        ) : unit ? (
          `${display} ${unit}`
        ) : (
          display
        )}
      </span>
    )
  }

  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      {right}
    </div>
  )
}

function InfoCard({
  title,
  fields,
  patient,
  style,
}: {
  title: string
  fields: { label: string; column: string }[]
  patient: Patient
  style: Style
}) {
  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {fields.map(({ label, column }) => {
          if (!(column in patient)) return null
          return (
            <InfoRow
              key={column}
              label={label}
              column={column}
              value={patient[column]}
              style={style}
            />
          )
        })}
      </CardContent>
    </Card>
  )
}

export function AdditionalInfo({ patient }: { patient: Patient }) {
  const names = Object.keys(SECTION_FIELDS)
  return (
    <div className="mt-8">
      <h3 className="text-base font-semibold mb-3">Additional Clinical Information</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
        <InfoCard title={names[0]} fields={SECTION_FIELDS[names[0]]} patient={patient} style="badge" />
        <InfoCard title={names[2]} fields={SECTION_FIELDS[names[2]]} patient={patient} style="alert" />
        <InfoCard title={names[1]} fields={SECTION_FIELDS[names[1]]} patient={patient} style="history" />
        <InfoCard title={names[3]} fields={SECTION_FIELDS[names[3]]} patient={patient} style="value" />
      </div>
    </div>
  )
}