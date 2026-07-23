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

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Parameter</TableHead>
          <TableHead>Value</TableHead>
          <TableHead className="text-center w-28">Severity</TableHead>
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

          return (
            <TableRow key={feature}>
              <TableCell className="font-medium">{excel_name}</TableCell>
              <TableCell className="tabular-nums">
                {value === null || value === undefined
                  ? '--'
                  : unit
                    ? `${value} ${unit}`
                    : String(value)}
              </TableCell>
              <TableCell className="text-center">
                <SeverityBadge level={level} label={label} />
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}