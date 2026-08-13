import { useEffect, useState } from 'react'
import type { Assessment, MonitoringData, PatientData } from '@/types'
import { DOMAINS, getLabel } from '@/config/domains'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { SeverityBadge } from './SeverityBadge'
import { getLevel } from '@/config/domains'
import { fetchMonitoring } from '@/api/client'
import { HhsTrendChart } from './monitoring/HhsTrendChart'
import { DomainTrendChart } from './monitoring/DomainTrendChart'
import { TrendInsightsCard } from './monitoring/TrendInsightsCard'
import { Loader2 } from 'lucide-react'

const FEATURE_TO_DOMAIN: Record<string, string> = {}
for (const [domain, info] of Object.entries(DOMAINS)) {
  for (const f of info.features) FEATURE_TO_DOMAIN[f] = domain
}

interface Props {
  patientId: string
  patientData: PatientData
  assessment: Assessment
  /**
   * How to load trends. Clinicians read a patient by id; a patient reads
   * /me/monitoring, which takes no id at all. Defaults to the clinician route.
   */
  loadMonitoring?: (patientId: string) => Promise<MonitoringData | null>
}

function ParameterSummary({ patientData }: { patientData: PatientData }) {
  const order: Record<string, number> = { '1': 0, '0.5': 1, '0': 2, null: 3 }
  const rows = Object.entries(patientData)
    .map(([feature, info]) => ({
      feature,
      Parameter: info.excel_name,
      Domain: FEATURE_TO_DOMAIN[feature] ?? 'Other',
      Value: info.value,
      Unit: info.unit,
      Severity: getLabel(info.severity),
      Level: getLevel(info.severity),
      sort: order[String(info.severity)] ?? 3,
    }))
    .sort(
      (a, b) =>
        a.sort - b.sort ||
        a.Domain.localeCompare(b.Domain) ||
        a.Parameter.localeCompare(b.Parameter),
    )

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Complete Parameter Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border max-h-[420px] overflow-auto">
          <Table>
            <TableHeader className="sticky top-0 bg-card z-[1]">
              <TableRow>
                <TableHead>Parameter</TableHead>
                <TableHead>Domain</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Unit</TableHead>
                <TableHead>Severity</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.feature}>
                  <TableCell className="font-medium">{r.Parameter}</TableCell>
                  <TableCell className="text-muted-foreground">{r.Domain}</TableCell>
                  <TableCell className="tabular-nums">{r.Value === null ? '--' : String(r.Value)}</TableCell>
                  <TableCell className="text-muted-foreground">{r.Unit}</TableCell>
                  <TableCell>
                    <SeverityBadge level={r.Level} label={r.Severity} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Longitudinal trends. Only patients with saved encounters have any, so this
 * renders an explicit empty state rather than a blank chart for CSV patients.
 */
function MonitoringSection({
  patientId,
  load,
}: {
  patientId: string
  load: (patientId: string) => Promise<MonitoringData | null>
}) {
  const [data, setData] = useState<MonitoringData | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let stale = false
    setLoading(true)
    setErr(null)
    load(patientId)
      .then((result) => {
        if (!stale) setData(result)
      })
      .catch((e) => {
        if (!stale) setErr(String(e))
      })
      .finally(() => {
        if (!stale) setLoading(false)
      })
    return () => {
      stale = true
    }
  }, [patientId, load])

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading visit history…
        </CardContent>
      </Card>
    )
  }

  if (err) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load visit history</AlertTitle>
        <AlertDescription>{err}</AlertDescription>
      </Alert>
    )
  }

  if (!data) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Visit History</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No saved encounters for this patient, so there is nothing to trend.
            History is recorded from the intake form onward; patients loaded from
            the internal CSV have none.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <HhsTrendChart trend={data.history.hhs_trend} />
      {/* Keyed so the per-domain visibility toggles reset when the patient
          changes; the default selection depends on that patient's burdens. */}
      <DomainTrendChart key={patientId} domainTrends={data.history.domain_trends} />
      <TrendInsightsCard insights={data.insights} visitCount={data.visit_count} />
    </>
  )
}

function BurdenBreakdown({ assessment }: { assessment: Assessment }) {
  const b = assessment.burden
  const rows = [
    { Component: 'Main Burden', Value: b.main },
    { Component: 'Treatment Residual', Value: b.treatment },
    { Component: 'Interaction Burden', Value: b.interaction },
    { Component: 'Total Burden', Value: b.total },
  ]
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Burden Breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Component</TableHead>
              <TableHead>Value</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.Component}>
                <TableCell className="font-medium">{r.Component}</TableCell>
                <TableCell>{r.Value}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function RedFlags({ assessment }: { assessment: Assessment }) {
  const flags = assessment.red_flags
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Critical Red Flags</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {flags.length === 0 ? (
          <Alert className="border-emerald-500/30 bg-emerald-500/5">
            <AlertTitle>All clear</AlertTitle>
            <AlertDescription>No critical red flags detected.</AlertDescription>
          </Alert>
        ) : (
          flags.map((flag) => (
            <Alert key={flag.flag} variant="destructive">
              <AlertDescription>{flag.message}</AlertDescription>
            </Alert>
          ))
        )}
      </CardContent>
    </Card>
  )
}

export function ParametersTab({
  patientId,
  patientData,
  assessment,
  loadMonitoring = fetchMonitoring,
}: Props) {
  return (
    <div className="space-y-4">
      <ParameterSummary patientData={patientData} />
      <MonitoringSection patientId={patientId} load={loadMonitoring} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <BurdenBreakdown assessment={assessment} />
        <RedFlags assessment={assessment} />
      </div>
    </div>
  )
}