import type { Assessment, PatientData } from '@/types'
import { OFFICIAL_DOMAIN_MAPPING, getLabel, getLevel } from '@/config/domains'
import { ParameterTable } from './ParameterTable'
import { SeverityBadge, SeverityDot } from './SeverityBadge'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  domainName: string
  weight: number
  features: string[]
  patientData: PatientData
  assessment: Assessment
  expanded: boolean
  onToggle: (open: boolean) => void
}

export function DomainCard({
  domainName,
  weight,
  features,
  patientData,
  assessment,
  expanded,
  onToggle,
}: Props) {
  const available = features.filter((f) => f in patientData)
  if (available.length === 0) return null

  const scores = available
    .map((f) => patientData[f].severity)
    .filter((s): s is number => s !== null)

  const visualSeverity = scores.includes(1) ? 1 : scores.includes(0.5) ? 0.5 : 0
  const level = getLevel(visualSeverity)
  const normalCount = scores.filter((s) => s === 0).length
  const borderlineCount = scores.filter((s) => s === 0.5).length
  const riskCount = scores.filter((s) => s === 1).length

  const officialDomain = OFFICIAL_DOMAIN_MAPPING[domainName]
  const domainSeverity = assessment.domain_severities[officialDomain] ?? 0

  return (
    <Collapsible open={expanded} onOpenChange={onToggle}>
      <div className="rounded-xl border bg-card shadow-xs transition-shadow hover:shadow-sm">
        <CollapsibleTrigger
          render={
            <button className="w-full text-left p-4 cursor-pointer group" />
          }
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0">
              <SeverityDot level={level} className="mt-1.5 h-2.5 w-2.5 shrink-0" />
              <div className="min-w-0">
                <h4 className="font-semibold text-sm leading-tight">
                  {domainName}
                </h4>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {available.length} parameter{available.length !== 1 ? 's' : ''}
                  {' · '}HHS severity {domainSeverity.toFixed(2)}
                  {' · '}weight {weight}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <SeverityBadge level={level} label={getLabel(visualSeverity)} />
              <ChevronDown
                className={cn(
                  'h-4 w-4 text-muted-foreground transition-transform',
                  expanded && 'rotate-180',
                )}
              />
            </div>
          </div>
          <div className="flex items-center gap-4 mt-3 ml-5 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <SeverityDot level="ok" className="h-1.5 w-1.5" />
              {normalCount} normal
            </span>
            <span className="inline-flex items-center gap-1.5">
              <SeverityDot level="warn" className="h-1.5 w-1.5" />
              {borderlineCount} borderline
            </span>
            <span className="inline-flex items-center gap-1.5">
              <SeverityDot level="risk" className="h-1.5 w-1.5" />
              {riskCount} at risk
            </span>
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="px-4 pb-4">
            <div className="rounded-lg border bg-background overflow-hidden">
              <ParameterTable features={available} patientData={patientData} />
            </div>
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}
