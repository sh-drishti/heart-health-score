import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

const VISIBLE = 10

interface Props {
  patientIds: string[]
  selectedPatient: string
  currentStart: string
  onNavigate: (selected: string, start: string) => void
}

export function PatientNav({ patientIds, selectedPatient, currentStart, onNavigate }: Props) {
  const total = patientIds.length
  if (total === 0) return null

  const startIndex = Math.max(0, patientIds.indexOf(currentStart))
  const visible = patientIds.slice(startIndex, startIndex + VISIBLE)
  const lastStartIdx = Math.max(0, total - VISIBLE)
  const selectedIndex = patientIds.indexOf(selectedPatient)

  const go = (start: string, sel: string) => onNavigate(sel, start)

  return (
    <div className="flex flex-wrap items-center gap-1 my-4">
      <span className="text-xs text-muted-foreground mr-2">
        Patient {selectedIndex + 1} of {total}
      </span>
      <Button
        variant="outline"
        size="icon-sm"
        title="First patient"
        onClick={() => go(patientIds[0], patientIds[0])}
      >
        <ChevronsLeft className="h-3.5 w-3.5" />
      </Button>
      <Button
        variant="outline"
        size="icon-sm"
        title="Previous patient"
        disabled={startIndex === 0}
        onClick={() => {
          if (startIndex > 0) {
            const p = patientIds[startIndex - 1]
            go(p, p)
          }
        }}
      >
        <ChevronLeft className="h-3.5 w-3.5" />
      </Button>

      {visible.map((patient, i) => (
        <Button
          key={patient}
          size="sm"
          variant={patient === selectedPatient ? 'default' : 'outline'}
          className="min-w-8 tabular-nums"
          title={patient}
          onClick={() => go(patient, patient)}
        >
          {startIndex + i + 1}
        </Button>
      ))}

      <Button
        variant="outline"
        size="icon-sm"
        title="Next patient"
        disabled={startIndex >= total - 1}
        onClick={() => {
          if (startIndex < total - 1) {
            const p = patientIds[startIndex + 1]
            go(p, p)
          }
        }}
      >
        <ChevronRight className="h-3.5 w-3.5" />
      </Button>
      <Button
        variant="outline"
        size="icon-sm"
        title="Last patient"
        onClick={() => {
          const p = patientIds[lastStartIdx]
          go(p, p)
        }}
      >
        <ChevronsRight className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}
