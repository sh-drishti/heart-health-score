import { useMemo, useState } from 'react'
import type { Assessment, PatientData } from '@/types'
import { DOMAINS, type SeverityLevel } from '@/config/domains'
import { DomainCard } from './DomainCard'
import { SeverityDot } from './SeverityBadge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

type Filter = 'All' | 'Risk' | 'Borderline' | 'Normal'
type SortMode = 'priority' | 'weight'

interface Props {
  patientData: PatientData
  assessment: Assessment
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

export function DomainSummary({ patientData, assessment }: Props) {
  const [expandAll, setExpandAll] = useState(false)
  const [openMap, setOpenMap] = useState<Record<string, boolean>>({})
  const [sortMode, setSortMode] = useState<SortMode>('priority')
  const [filter, setFilter] = useState<Filter>('All')

  const ordered = useMemo(() => {
    const entries = Object.entries(DOMAINS)
    if (sortMode === 'weight') {
      return entries.sort((a, b) => b[1].weight - a[1].weight)
    }
    return entries.sort((a, b) => {
      const sevDiff =
        getDomainSeverity(b[1].features, patientData) -
        getDomainSeverity(a[1].features, patientData)
      return sevDiff !== 0 ? sevDiff : b[1].weight - a[1].weight
    })
  }, [sortMode, patientData])

  const filtered = ordered.filter(([, info]) => {
    if (filter === 'All') return true
    const sev = getDomainSeverity(info.features, patientData)
    if (filter === 'Risk') return sev === 1
    if (filter === 'Borderline') return sev === 0.5
    return sev === 0
  })

  const isOpen = (name: string) => openMap[name] ?? expandAll

  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mb-5">
        <div className="inline-flex items-center rounded-lg border bg-card p-0.5">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer',
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

        <Select value={sortMode} onValueChange={(v) => setSortMode(v as SortMode)}>
          <SelectTrigger className="w-52 h-8! text-xs">
            <SelectValue placeholder="Sort Domains By" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="priority">Clinical Priority</SelectItem>
            <SelectItem value="weight">HHS Report Weight</SelectItem>
          </SelectContent>
        </Select>

        <div className="flex gap-2 ml-auto">
          <Button
            variant="ghost"
            size="sm"
            className="text-xs"
            onClick={() => {
              setExpandAll(true)
              setOpenMap({})
            }}
          >
            Expand All
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-xs"
            onClick={() => {
              setExpandAll(false)
              setOpenMap({})
            }}
          >
            Collapse All
          </Button>
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">
          No {filter.toLowerCase()} domains found.
        </p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 items-start">
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