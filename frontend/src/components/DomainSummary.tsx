import { useMemo, useState, type ReactNode } from 'react'
import type { Assessment, PatientData } from '@/types'
import { DOMAINS, type SeverityLevel } from '@/config/domains'
import { DomainCard } from './DomainCard'
import { SeverityDot } from './SeverityBadge'
import { Button } from '@/components/ui/button'
import { ChevronsDownUp, ChevronsUpDown } from 'lucide-react'
import { cn } from '@/lib/utils'

type Filter = 'All' | 'Risk' | 'Borderline' | 'Normal'

interface Props {
  patientData: PatientData
  assessment: Assessment
  /** Rendered at the end of the toolbar, e.g. the "All parameters" button. */
  actions?: ReactNode
}

function getDomainSeverity(features: string[], patientData: PatientData): number {
  const sevs = features
    .filter((f) => f in patientData)
    .map((f) => patientData[f].severity)
    .filter((s): s is number => s !== null)
  if (sevs.length === 0) return -1
  return Math.max(...sevs)
}

const FILTERS: { value: Filter; label: string; level?: SeverityLevel }[] = [
  { value: 'All', label: 'All' },
  { value: 'Risk', label: 'Risk', level: 'risk' },
  { value: 'Borderline', label: 'Borderline', level: 'warn' },
  { value: 'Normal', label: 'Normal', level: 'ok' },
]

export function DomainSummary({ patientData, assessment, actions }: Props) {
  const [openMap, setOpenMap] = useState<Record<string, boolean>>({})
  const [filter, setFilter] = useState<Filter>('All')

  // Domains with a parameter at risk first, then borderline, then normal; ties
  // go to the domain with the larger weight in the HHS formula.
  const ordered = useMemo(
    () =>
      Object.entries(DOMAINS).sort((a, b) => {
        const sevDiff =
          getDomainSeverity(b[1].features, patientData) -
          getDomainSeverity(a[1].features, patientData)
        return sevDiff !== 0 ? sevDiff : b[1].weight - a[1].weight
      }),
    [patientData],
  )

  // A domain with none of its parameters on file renders nothing (see
  // DomainCard), so it must not count towards "everything is expanded".
  const filtered = ordered.filter(([, info]) => {
    if (!info.features.some((f) => f in patientData)) return false
    if (filter === 'All') return true
    const sev = getDomainSeverity(info.features, patientData)
    if (filter === 'Risk') return sev === 1
    if (filter === 'Borderline') return sev === 0.5
    return sev === 0
  })

  const isOpen = (name: string) => openMap[name] ?? false
  const allOpen = filtered.length > 0 && filtered.every(([name]) => isOpen(name))

  const toggleAll = () =>
    setOpenMap(Object.fromEntries(filtered.map(([name]) => [name, !allOpen])))

  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mb-4">
        <div className="inline-flex items-center rounded-md border bg-card p-0.5">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-sm px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer',
                filter === f.value
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {f.level && <SeverityDot level={f.level} className="h-1.5 w-1.5" />}
              {f.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 ml-auto">
          <Button
            variant="outline"
            size="sm"
            className="text-xs"
            onClick={toggleAll}
            disabled={filtered.length === 0}
          >
            {allOpen ? (
              <>
                <ChevronsDownUp className="h-3.5 w-3.5" /> Collapse all
              </>
            ) : (
              <>
                <ChevronsUpDown className="h-3.5 w-3.5" /> Expand all
              </>
            )}
          </Button>
          {actions}
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">
          No {filter === 'All' ? '' : `${filter.toLowerCase()} `}domains found.
        </p>
      ) : (
        // Collapsed cards share a row and stretch to one height. An expanded
        // card takes a whole row, so it never leaves a neighbour stretched or
        // a hole beside it; dense packing lets later cards close the gap.
        <div className="grid grid-cols-[repeat(auto-fill,minmax(min(22rem,100%),1fr))] grid-flow-row-dense gap-3 items-stretch">
          {filtered.map(([name, info]) => (
            <DomainCard
              key={name}
              domainName={name}
              weight={info.weight}
              features={info.features}
              patientData={patientData}
              assessment={assessment}
              expanded={isOpen(name)}
              onToggle={(open) => setOpenMap((m) => ({ ...m, [name]: open }))}
            />
          ))}
        </div>
      )}
    </div>
  )
}
