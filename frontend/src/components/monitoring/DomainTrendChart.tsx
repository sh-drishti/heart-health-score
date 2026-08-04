import { useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import type { DomainTrendPoint } from '@/types'
import { cn } from '@/lib/utils'
import { formatAxisDate, formatFullDate } from './format'

// Ten domains, so the five --chart-* tokens are not enough. These are picked to
// stay distinguishable in both themes.
const PALETTE = [
  '#0d9488', '#6366f1', '#f59e0b', '#8b5cf6', '#0ea5e9',
  '#f43f5e', '#84cc16', '#ec4899', '#14b8a6', '#64748b',
]

// Domain names contain spaces and slashes; ChartContainer turns config keys into
// `--color-<key>` CSS variables, so they have to be identifier-safe.
function slug(domain: string): string {
  return domain.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '')
}

interface Row {
  date: string
  [key: string]: string | number
}

export function DomainTrendChart({
  domainTrends,
}: {
  domainTrends: Record<string, DomainTrendPoint[]>
}) {
  const { config, keys, rows } = useMemo(() => {
    // Order domains by their latest burden so the worst offenders read first.
    const domains = Object.keys(domainTrends).sort((a, b) => {
      const last = (d: string) => domainTrends[d]?.at(-1)?.burden ?? 0
      return last(b) - last(a)
    })

    const config: ChartConfig = {}
    const keys: { key: string; domain: string; color: string }[] = []
    domains.forEach((domain, i) => {
      const key = slug(domain)
      const color = PALETTE[i % PALETTE.length]
      config[key] = { label: domain, color }
      keys.push({ key, domain, color })
    })

    // Pivot {domain: [{date, burden}]} into one row per encounter date.
    const byDate = new Map<string, Row>()
    for (const { key, domain } of keys) {
      for (const point of domainTrends[domain]) {
        const row = byDate.get(point.date) ?? { date: point.date }
        row[key] = point.burden
        byDate.set(point.date, row)
      }
    }
    const rows = [...byDate.values()].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
    )

    return { config, keys, rows }
  }, [domainTrends])

  // Default to the four highest-burden domains; ten lines at once is unreadable.
  const [hidden, setHidden] = useState<Set<string>>(
    () => new Set(keys.slice(4).map((k) => k.key)),
  )

  const toggle = (key: string) =>
    setHidden((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })

  const visible = keys.filter((k) => !hidden.has(k.key))

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Domain Burden Trend</CardTitle>
        <CardDescription>
          Total contribution per domain across visits. Lower is better.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-1.5 mb-4">
          {keys.map(({ key, domain, color }) => {
            const on = !hidden.has(key)
            return (
              <button
                key={key}
                type="button"
                onClick={() => toggle(key)}
                aria-pressed={on}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors',
                  on
                    ? 'bg-muted/60 text-foreground'
                    : 'text-muted-foreground opacity-60 hover:opacity-100',
                )}
              >
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ background: on ? color : 'transparent', boxShadow: `inset 0 0 0 1px ${color}` }}
                />
                {domain}
              </button>
            )
          })}
        </div>

        <ChartContainer config={config} className="aspect-auto h-[280px] w-full">
          <LineChart accessibilityLayer data={rows} margin={{ left: 12, right: 12 }}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              minTickGap={24}
              tickFormatter={formatAxisDate}
            />
            <YAxis tickLine={false} axisLine={false} tickMargin={8} width={36} />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  className="w-[230px]"
                  labelFormatter={formatFullDate}
                  formatter={(value, name) => (
                    <>
                      <div
                        className="h-2.5 w-2.5 shrink-0 rounded-[2px]"
                        style={{ background: `var(--color-${name})` }}
                      />
                      <div className="flex flex-1 justify-between gap-2 leading-none">
                        <span className="text-muted-foreground">
                          {(config[name as string]?.label as string) ?? name}
                        </span>
                        <span className="font-mono font-medium tabular-nums">
                          {Number(value).toFixed(2)}
                        </span>
                      </div>
                    </>
                  )}
                />
              }
            />
            {visible.map(({ key }) => (
              <Line
                key={key}
                dataKey={key}
                type="monotone"
                stroke={`var(--color-${key})`}
                strokeWidth={2}
                dot={rows.length <= 12}
                connectNulls
              />
            ))}
          </LineChart>
        </ChartContainer>

        {visible.length === 0 && (
          <p className="text-xs text-muted-foreground mt-2">
            No domains selected. Pick one above to plot it.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
