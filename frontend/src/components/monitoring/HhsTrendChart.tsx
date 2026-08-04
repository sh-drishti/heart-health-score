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
import type { HhsTrendPoint } from '@/types'
import { formatAxisDate, formatFullDate } from './format'

const chartConfig = {
  hhs: { label: 'Heart Health Score', color: 'var(--chart-1)' },
  confidence: { label: 'Data Confidence', color: 'var(--chart-3)' },
} satisfies ChartConfig

type Metric = keyof typeof chartConfig

export function HhsTrendChart({ trend }: { trend: HhsTrendPoint[] }) {
  const [active, setActive] = useState<Metric>('hhs')

  // Both series are 0-100, so a fixed domain keeps the vertical scale
  // comparable when toggling between them.
  const latest = useMemo(() => trend[trend.length - 1], [trend])

  return (
    <Card className="py-4 sm:py-0">
      <CardHeader className="flex flex-col items-stretch border-b p-0! sm:flex-row">
        <div className="flex flex-1 flex-col justify-center gap-1 px-6 pb-3 sm:pb-0">
          <CardTitle className="text-base">Heart Health Score Trend</CardTitle>
          <CardDescription>
            {trend.length === 1
              ? 'One recorded visit — a trend appears from the second visit onward.'
              : `${trend.length} recorded visits`}
          </CardDescription>
        </div>
        <div className="flex">
          {(Object.keys(chartConfig) as Metric[]).map((metric) => (
            <button
              key={metric}
              type="button"
              data-active={active === metric}
              className="flex flex-1 flex-col justify-center gap-1 border-t px-6 py-4 text-left even:border-l data-[active=true]:bg-muted/50 sm:border-t-0 sm:border-l sm:px-8 sm:py-4"
              onClick={() => setActive(metric)}
            >
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                {chartConfig[metric].label}
              </span>
              <span className="text-lg leading-none font-bold sm:text-2xl tabular-nums">
                {latest?.[metric]?.toFixed(1) ?? '--'}
              </span>
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="px-2 sm:p-6">
        <ChartContainer config={chartConfig} className="aspect-auto h-[250px] w-full">
          <LineChart accessibilityLayer data={trend} margin={{ left: 12, right: 12 }}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              minTickGap={24}
              tickFormatter={formatAxisDate}
            />
            <YAxis
              domain={[0, 100]}
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              width={36}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  className="w-[190px]"
                  labelFormatter={formatFullDate}
                  formatter={(value, name) => (
                    <>
                      <div
                        className="h-2.5 w-2.5 shrink-0 rounded-[2px]"
                        style={{ background: `var(--color-${name})` }}
                      />
                      <div className="flex flex-1 justify-between gap-2 leading-none">
                        <span className="text-muted-foreground">
                          {chartConfig[name as Metric]?.label ?? name}
                        </span>
                        <span className="font-mono font-medium tabular-nums">
                          {Number(value).toFixed(1)}
                        </span>
                      </div>
                    </>
                  )}
                />
              }
            />
            <Line
              dataKey={active}
              type="monotone"
              stroke={`var(--color-${active})`}
              strokeWidth={2}
              dot={trend.length <= 12}
            />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
