import { useEffect, useState } from 'react'
import type { Assessment, MonitoringData } from '@/types'
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
import { fetchMonitoring } from '@/api/client'
import { HhsTrendChart } from './monitoring/HhsTrendChart'
import { DomainTrendChart } from './monitoring/DomainTrendChart'
import { TrendInsightsCard } from './monitoring/TrendInsightsCard'
import { Loader2 } from 'lucide-react'

interface Props {
  patientId: string
  assessment: Assessment
  /**
   * How to load trends. Clinicians read a patient by id; a patient reads
   * /me/monitoring, which takes no id at all. Defaults to the clinician route.
   */
  loadMonitoring?: (patientId: string) => Promise<MonitoringData | null>
}

function BurdenBreakdown({ assessment }: { assessment: Assessment }) {
  const b = assessment.burden
  const rows = [
    { Component: 'Main Burden', Value: b.main },
    { Component: 'Treatment Residual', Value: b.treatment },
    { Component: 'Interaction Burden', Value: b.interaction },
  ]
  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle>Burden Breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Component</TableHead>
              <TableHead className="text-right">Value</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.Component}>
                <TableCell>{r.Component}</TableCell>
                <TableCell className="text-right tabular-nums">{r.Value}</TableCell>
              </TableRow>
            ))}
            <TableRow className="font-semibold">
              <TableCell>Total Burden</TableCell>
              <TableCell className="text-right tabular-nums">{b.total}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <p className="text-xs text-muted-foreground mt-3">
          The score is 100 minus the total burden, so lower burden is better.
        </p>
      </CardContent>
    </Card>
  )
}

/**
 * Trends and burden as a 2x2 grid: score trend and domain trend on top,
 * insights and the current burden underneath. The charts fit their cell at any
 * visit count — the axis thins its labels and the dots drop out past a couple
 * of dozen visits — so nothing scrolls sideways.
 */
export function TrendsSection({ patientId, assessment, loadMonitoring = fetchMonitoring }: Props) {
  const [data, setData] = useState<MonitoringData | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let stale = false
    setLoading(true)
    setErr(null)
    loadMonitoring(patientId)
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
  }, [patientId, loadMonitoring])

  let history: React.ReactNode
  if (loading) {
    history = (
      <Card className="md:col-span-2">
        <CardContent className="py-8 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading visit history…
        </CardContent>
      </Card>
    )
  } else if (err) {
    history = (
      <Alert variant="destructive" className="md:col-span-2">
        <AlertTitle>Could not load visit history</AlertTitle>
        <AlertDescription>{err}</AlertDescription>
      </Alert>
    )
  } else if (!data) {
    history = (
      <Card className="md:col-span-2">
        <CardHeader className="pb-2">
          <CardTitle>Visit History</CardTitle>
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
  } else {
    history = (
      <>
        <HhsTrendChart trend={data.history.hhs_trend} />
        {/* Keyed so the per-domain visibility toggles reset when the patient
            changes; the default selection depends on that patient's burdens. */}
        <DomainTrendChart key={patientId} domainTrends={data.history.domain_trends} />
        <TrendInsightsCard insights={data.insights} visitCount={data.visit_count} />
      </>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">
      {history}
      <BurdenBreakdown assessment={assessment} />
    </div>
  )
}
