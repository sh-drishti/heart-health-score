import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { TrendingDown, TrendingUp } from 'lucide-react'
import type { TrendInsights } from '@/types'

export function TrendInsightsCard({
  insights,
  visitCount,
}: {
  insights: TrendInsights
  visitCount: number
}) {
  const attention = insights.attention_required ?? []
  const progress = insights.positive_progress ?? []

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Trend Insights</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {visitCount < 2 ? (
          <p className="text-sm text-muted-foreground">
            Insights compare the first and most recent visit. At least two visits
            are needed.
          </p>
        ) : (
          <>
            <section className="space-y-2">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <TrendingDown className="h-3.5 w-3.5" /> Attention required
              </h4>
              {attention.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No significant deterioration since the first visit.
                </p>
              ) : (
                attention.map((item) => (
                  <Alert key={item} variant="destructive">
                    <AlertDescription>{item}</AlertDescription>
                  </Alert>
                ))
              )}
            </section>

            <section className="space-y-2">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <TrendingUp className="h-3.5 w-3.5" /> Positive progress
              </h4>
              {progress.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No significant improvement since the first visit.
                </p>
              ) : (
                progress.map((item) => (
                  <Alert key={item} className="border-emerald-500/30 bg-emerald-500/5">
                    <AlertDescription>{item}</AlertDescription>
                  </Alert>
                ))
              )}
            </section>
          </>
        )}
      </CardContent>
    </Card>
  )
}
