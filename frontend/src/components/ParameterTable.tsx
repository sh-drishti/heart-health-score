import type { PatientData } from '@/types'
import { getLabel, getLevel, type SeverityLevel } from '@/config/domains'
import { SeverityBadge } from './SeverityBadge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface Props {
  features: string[]
  patientData: PatientData
}

function severityKey(feature: string, patientData: PatientData): [number, number] {
  const sev = patientData[feature]?.severity ?? null
  if (sev === null) return [1, 0]
  return [0, -sev]
}

export function ParameterTable({ features, patientData }: Props) {
  const available = features.filter((f) => f in patientData)
  const sorted = [...available].sort((a, b) => {
    const ka = severityKey(a, patientData)
    const kb = severityKey(b, patientData)
    return ka[0] - kb[0] || ka[1] - kb[1]
  })

  // A container query, not a breakpoint: two cards share a row, so a card can
  // be narrow on a wide screen. Below 28rem the value moves under the
  // parameter name instead of taking a column of its own, so nothing scrolls
  // sideways.
  return (
    <div className="@container">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Parameter</TableHead>
            <TableHead className="hidden @md:table-cell">Value</TableHead>
            <TableHead className="text-right w-px">Severity</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((feature) => {
            const info = patientData[feature]
            const { value, severity, excel_name, unit } = info

            let level: SeverityLevel
            let label: string
            if (value === null || value === undefined) {
              level = 'neutral'
              label = 'Missing'
            } else if (severity === null) {
              level = 'neutral'
              label = 'N/A'
            } else {
              level = getLevel(severity)
              label = getLabel(severity)
            }

            const shown =
              value === null || value === undefined
                ? '--'
                : unit
                  ? `${value} ${unit}`
                  : String(value)

            return (
              <TableRow key={feature}>
                <TableCell className="font-medium whitespace-normal">
                  {excel_name}
                  <div className="@md:hidden mt-0.5 text-xs font-normal text-muted-foreground tabular-nums">
                    {shown}
                  </div>
                </TableCell>
                <TableCell className="hidden @md:table-cell tabular-nums">{shown}</TableCell>
                <TableCell className="text-right">
                  <SeverityBadge level={level} label={label} />
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}