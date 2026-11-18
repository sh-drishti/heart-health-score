import { useMemo, useState } from 'react'
import { Dialog } from '@base-ui/react/dialog'
import type { PatientData } from '@/types'
import { DOMAINS, getLabel, getLevel } from '@/config/domains'
import { SeverityBadge } from './SeverityBadge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ListTree, Search, X } from 'lucide-react'

const FEATURE_TO_DOMAIN: Record<string, string> = {}
for (const [domain, info] of Object.entries(DOMAINS)) {
  for (const f of info.features) FEATURE_TO_DOMAIN[f] = domain
}

// A MongoDB-sourced patient carries `<key>_status` and `<key>_months_old` next
// to each value. They describe a parameter rather than being one, and listing
// them doubled the table with rows like "Sbp Months Old".
function isParameter(key: string): boolean {
  return !key.endsWith('_status') && !key.endsWith('_months_old')
}

const SEVERITY_ORDER: Record<string, number> = { '1': 0, '0.5': 1, '0': 2 }

/**
 * Every parameter on file, in a panel that slides over the page. It is long,
 * so it lives behind a button instead of pushing the trends off-screen.
 */
export function AllParametersSheet({ patientData }: { patientData: PatientData }) {
  const [query, setQuery] = useState('')

  const rows = useMemo(
    () =>
      Object.entries(patientData)
        .filter(([key]) => isParameter(key))
        .map(([feature, info]) => ({
          feature,
          parameter: info.excel_name,
          domain: FEATURE_TO_DOMAIN[feature] ?? 'Other',
          value: info.value,
          unit: info.unit,
          severity: info.severity,
          sort: SEVERITY_ORDER[String(info.severity)] ?? 3,
        }))
        .sort(
          (a, b) =>
            a.sort - b.sort ||
            a.domain.localeCompare(b.domain) ||
            a.parameter.localeCompare(b.parameter),
        ),
    [patientData],
  )

  const q = query.trim().toLowerCase()
  const shown = q
    ? rows.filter(
        (r) => r.parameter.toLowerCase().includes(q) || r.domain.toLowerCase().includes(q),
      )
    : rows

  return (
    <Dialog.Root onOpenChange={(open) => !open && setQuery('')}>
      <Dialog.Trigger render={<Button variant="outline" size="sm" className="text-xs" />}>
        <ListTree className="h-3.5 w-3.5" />
        All parameters ({rows.length})
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-40 bg-black/30 transition-opacity duration-200 data-[starting-style]:opacity-0 data-[ending-style]:opacity-0" />
        <Dialog.Popup className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col border-l bg-card shadow-xl outline-none transition-transform duration-200 data-[starting-style]:translate-x-full data-[ending-style]:translate-x-full">
          <div className="flex items-center justify-between gap-3 border-b px-5 py-3">
            <div>
              <Dialog.Title className="section-title">All Parameters</Dialog.Title>
              <Dialog.Description className="text-xs text-muted-foreground">
                {rows.length} on file, most at risk first.
              </Dialog.Description>
            </div>
            <Dialog.Close render={<Button variant="ghost" size="icon" aria-label="Close" />}>
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>

          <div className="px-5 py-3 border-b">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter by parameter or domain…"
                className="pl-8 h-8 text-sm"
                aria-label="Filter parameters"
              />
            </div>
          </div>

          <div className="flex-1 overflow-auto">
            <Table>
              <TableHeader className="sticky top-0 bg-card z-[1]">
                <TableRow>
                  <TableHead className="pl-5">Parameter</TableHead>
                  <TableHead>Domain</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead className="pr-5">Severity</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shown.map((r) => (
                  <TableRow key={r.feature}>
                    <TableCell className="pl-5 font-medium whitespace-normal">{r.parameter}</TableCell>
                    <TableCell className="text-muted-foreground whitespace-normal">{r.domain}</TableCell>
                    <TableCell className="tabular-nums">
                      {r.value === null || r.value === undefined
                        ? '--'
                        : r.unit
                          ? `${r.value} ${r.unit}`
                          : String(r.value)}
                    </TableCell>
                    <TableCell className="pr-5">
                      <SeverityBadge level={getLevel(r.severity)} label={getLabel(r.severity)} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {shown.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-8">
                No parameters match “{query}”.
              </p>
            )}
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
