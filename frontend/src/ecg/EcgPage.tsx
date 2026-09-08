import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle2, Info, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AppHeader } from '@/components/AppHeader'
import {
  EcgError,
  fetchEcgSchema,
  interpret,
  type EcgResult,
  type EcgSchema,
} from './api'

// ECG interpretation from five interval measurements.
//
// Standalone: nothing is read from or written to a patient record, and no
// result is stored. Enter five numbers, get a reading back.
//
// The model behind this is multilabel with independent, tuned thresholds, which
// has two consequences the interface has to be honest about: "Normal" can be
// positive at the same time as an abnormality, and the four abnormal classes
// tend to move together. So the page leads with a single verdict, shows every
// probability against its own threshold, and never claims a diagnosis.

/** QTc by Bazett — QT / sqrt(RR). Matches the reference case shipped with the
 *  model: QT 323 at HR 103 gives 423. */
function bazett(qt: number, hr: number): number {
  return Math.round((qt / Math.sqrt(60 / hr)) * 10) / 10
}

const EMPTY: Record<string, string> = {
  heart_rate: '',
  pr_interval: '',
  qrs_duration: '',
  qt_interval: '',
  qtc_interval: '',
}

export function EcgPage() {
  const [schema, setSchema] = useState<EcgSchema | null>(null)
  const [values, setValues] = useState<Record<string, string>>(EMPTY)
  const [qtcTouched, setQtcTouched] = useState(false)

  const [result, setResult] = useState<EcgResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    fetchEcgSchema()
      .then(setSchema)
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)))
  }, [])

  // QTc is derived from QT and heart rate, so prefill it rather than making
  // someone compute it. Stops the moment they type their own value.
  useEffect(() => {
    if (qtcTouched) return
    const qt = Number(values.qt_interval)
    const hr = Number(values.heart_rate)
    if (values.qt_interval && values.heart_rate && qt > 0 && hr > 0) {
      setValues((v) => ({ ...v, qtc_interval: String(bazett(qt, hr)) }))
    }
  }, [values.qt_interval, values.heart_rate, qtcTouched])

  const set = (key: string, value: string) => {
    if (key === 'qtc_interval') setQtcTouched(true)
    setValues((v) => ({ ...v, [key]: value }))
  }

  const run = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setErr(null)
    setFieldErrors({})
    setResult(null)

    const payload: Record<string, number | null> = {}
    for (const key of Object.keys(EMPTY)) {
      payload[key] = values[key] === '' ? null : Number(values[key])
    }

    try {
      setResult(await interpret(payload))
    } catch (e) {
      if (e instanceof EcgError && e.fieldErrors.length > 0) {
        const map: Record<string, string> = {}
        for (const fe of e.fieldErrors) map[fe.field] = fe.message
        setFieldErrors(map)
        setErr(e.message)
      } else {
        setErr(e instanceof Error ? e.message : String(e))
      }
    } finally {
      setBusy(false)
    }
  }

  const reset = () => {
    setValues(EMPTY)
    setQtcTouched(false)
    setResult(null)
    setErr(null)
    setFieldErrors({})
  }

  return (
    <div className="min-h-screen bg-background">
      <AppHeader subtitle="ECG Interpretation" />
      <main className="max-w-[900px] mx-auto px-6 py-8">
        <div className="mb-7">
          <h1 className="text-2xl font-semibold tracking-tight mb-1.5">
            ECG interpretation
          </h1>
          <p className="text-muted-foreground text-sm max-w-[64ch]">
            Enter five interval measurements. Nothing here is saved, and this is not
            linked to any patient record.
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)] items-start">
          {/* ---- inputs ---- */}
          <form onSubmit={run} className="rounded-lg border bg-card p-5">
            <h2 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-4">
              Measurements
            </h2>

            <div className="space-y-4">
              {(schema?.fields ?? []).map((field) => (
                <div key={field.key} className="space-y-1.5">
                  <div className="flex items-baseline justify-between gap-2">
                    <Label htmlFor={field.key}>{field.label}</Label>
                    <span className="text-[11px] text-muted-foreground tabular-nums">
                      {field.min}–{field.max} {field.unit}
                    </span>
                  </div>
                  <Input
                    id={field.key}
                    type="number"
                    step="any"
                    inputMode="decimal"
                    value={values[field.key]}
                    onChange={(e) => set(field.key, e.target.value)}
                    aria-invalid={fieldErrors[field.key] ? true : undefined}
                  />
                  {field.key === 'qtc_interval' && !qtcTouched && values.qtc_interval && (
                    <p className="text-[11px] text-muted-foreground">
                      Calculated from QT and heart rate (Bazett). Type to override.
                    </p>
                  )}
                  {fieldErrors[field.key] && (
                    <p className="text-xs text-destructive" role="alert">
                      {fieldErrors[field.key]}
                    </p>
                  )}
                </div>
              ))}
            </div>

            {err && !Object.keys(fieldErrors).length && (
              <p className="text-sm text-destructive mt-4" role="alert">
                {err}
              </p>
            )}

            <div className="flex gap-2 mt-6">
              <Button type="submit" disabled={busy || !schema} className="flex-1">
                {busy && <Loader2 className="size-4 animate-spin" />}
                Interpret
              </Button>
              <Button type="button" variant="outline" onClick={reset}>
                Clear
              </Button>
            </div>
          </form>

          {/* ---- result ---- */}
          <div>
            {!result ? (
              <div className="rounded-lg border border-dashed py-24 text-center text-muted-foreground">
                <Activity className="size-7 mx-auto mb-3 opacity-40" />
                <p className="text-sm">Enter measurements to see a reading.</p>
              </div>
            ) : (
              <div className="space-y-5">
                <div
                  className={`rounded-lg border p-5 ${
                    result.status === 'normal'
                      ? 'border-emerald-500/30 bg-emerald-500/5'
                      : 'border-amber-500/40 bg-amber-500/5'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {result.status === 'normal' ? (
                      <CheckCircle2 className="size-5 mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
                    ) : (
                      <AlertTriangle className="size-5 mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
                    )}
                    <div>
                      <h2 className="font-semibold mb-1">
                        {result.status === 'normal'
                          ? 'No abnormality flagged'
                          : 'Review suggested'}
                      </h2>
                      <p className="text-sm text-muted-foreground">
                        {result.status === 'normal'
                          ? 'None of the four abnormality indicators reached its threshold.'
                          : `${result.abnormalities.length} of 4 abnormality indicators reached threshold. This is a screening signal, not a diagnosis.`}
                      </p>
                    </div>
                  </div>
                </div>

                {result.norm_and_abnormal && (
                  <div className="rounded-lg border p-4 flex gap-3">
                    <Info className="size-4 mt-0.5 shrink-0 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">
                      “Normal ECG” also reached its threshold here. The model scores
                      each of the five independently, so they can be positive at the
                      same time — a property of the model, not a contradiction in the
                      reading.
                    </p>
                  </div>
                )}

                <div className="rounded-lg border">
                  <div className="px-5 py-3 border-b">
                    <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      All indicators
                    </h3>
                  </div>
                  <div className="divide-y">
                    {Object.entries(result.predictions).map(([key, p]) => (
                      <div key={key} className="px-5 py-3">
                        <div className="flex items-baseline justify-between gap-3 mb-1.5">
                          <span className="text-sm font-medium">{p.label}</span>
                          <span className="text-xs tabular-nums text-muted-foreground">
                            {(p.probability * 100).toFixed(1)}% · threshold{' '}
                            {(p.threshold * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="relative h-1.5 rounded-full bg-muted overflow-hidden">
                          <div
                            className={`absolute inset-y-0 left-0 rounded-full ${
                              p.positive ? 'bg-primary' : 'bg-muted-foreground/40'
                            }`}
                            style={{ width: `${Math.min(p.probability * 100, 100)}%` }}
                          />
                          <div
                            className="absolute inset-y-0 w-px bg-foreground/50"
                            style={{ left: `${Math.min(p.threshold * 100, 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <p className="text-xs text-muted-foreground">
                  Model {result.model_version}. Trained on PTB-XL. Screening support
                  only — it does not replace a clinician reading the trace.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
