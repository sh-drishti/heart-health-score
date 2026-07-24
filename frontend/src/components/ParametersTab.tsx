import type { Assessment, PatientData } from '@/types'
import { DOMAINS, getLabel, SEVERITY_HEX } from '@/config/domains'
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
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'

const FEATURE_TO_DOMAIN: Record<string, string> = {}
for (const [domain, info] of Object.entries(DOMAINS)) {
  for (const f of info.features) FEATURE_TO_DOMAIN[f] = domain
}

interface Props {
  patientData: PatientData
  assessment: Assessment
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

function ContributionChart({ assessment }: { assessment: Assessment }) {
  const data = assessment.domain_rows
    .filter((r) => r['Total domain contribution'] > 0)
    .map((r) => ({ name: r.Domain, value: r['Total domain contribution'] }))

  const COLORS = [
    '#0d9488', '#6366f1', '#f59e0b', '#8b5cf6', '#14b8a6',
    '#f43f5e', '#84cc16', '#06b6d4', '#a855f7', '#64748b',
  ]

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Domain Contribution to HHS</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative h-[380px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                innerRadius="55%"
                outerRadius="85%"
                paddingAngle={2}
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => [Number(v).toFixed(2)]}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center -mt-6">
              <div className="text-xs text-muted-foreground">Total</div>
              <div className="text-xl font-bold">{assessment.burden.total.toFixed(2)}</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function SeverityChart({ assessment }: { assessment: Assessment }) {
  const data = Object.entries(assessment.domain_severities)
    .map(([domain, severity]) => {
      const status = severity < 0.33 ? 'Low' : severity < 0.67 ? 'Moderate' : 'High'
      return { domain, severity, status }
    })
    .sort((a, b) => a.severity - b.severity)

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Domain Severity Overview</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[380px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ left: 20, right: 40 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" domain={[0, 1]} />
              <YAxis type="category" dataKey="domain" width={110} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v) => Number(v).toFixed(2)} />
              <Bar dataKey="severity" radius={[0, 4, 4, 0]}>
                {data.map((d, i) => (
                  <Cell
                    key={i}
                    fill={
                      d.status === 'Low'
                        ? SEVERITY_HEX.ok
                        : d.status === 'Moderate'
                          ? SEVERITY_HEX.warn
                          : SEVERITY_HEX.risk
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
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
          flags.map((flag, i) => (
            <Alert key={i} variant="destructive">
              <AlertDescription>{flag}</AlertDescription>
            </Alert>
          ))
        )}
      </CardContent>
    </Card>
  )
}

export function ParametersTab({ patientData, assessment }: Props) {
  return (
    <div className="space-y-4">
      <ParameterSummary patientData={patientData} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ContributionChart assessment={assessment} />
        <SeverityChart assessment={assessment} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <BurdenBreakdown assessment={assessment} />
        <RedFlags assessment={assessment} />
      </div>
    </div>
  )
}