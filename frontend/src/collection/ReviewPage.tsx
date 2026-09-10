import { Fragment, useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Download,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ThemeToggle } from '@/components/ThemeToggle'
import {
  downloadCsv,
  fetchSubmissions,
  type FieldDef,
  type Review,
  type StoredAnswer,
  type Submission,
} from './api'

// Review of collected parameters, behind its own code.
//
// The code is typed, never carried in the URL — unlike the submission link.
// This page reads everybody's health data, and a query string is written to
// nginx access logs and browser history.
//
// Temporary, like the rest of this directory.

function answerText(answer: StoredAnswer | undefined): string {
  if (!answer) return '—'
  if (answer.unknown) return 'Unknown'
  return answer.value === null || answer.value === '' ? '—' : String(answer.value)
}

function when(iso: string): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function countUnknown(submission: Submission, fields: FieldDef[]): number {
  return fields.filter((f) => submission.answers[f.key]?.unknown).length
}

export function ReviewPage() {
  const [adminCode, setAdminCode] = useState('')
  const [review, setReview] = useState<Review | null>(null)
  const [open, setOpen] = useState<string | null>(null)

  const [busy, setBusy] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const load = async (code: string) => {
    setBusy(true)
    setErr(null)
    try {
      setReview(await fetchSubmissions(code))
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const save = async () => {
    setDownloading(true)
    setErr(null)
    try {
      await downloadCsv(adminCode.trim())
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setDownloading(false)
    }
  }

  const shell = (children: React.ReactNode) => (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b bg-card/80 backdrop-blur">
        <div className="max-w-[1100px] mx-auto px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Users className="size-5 text-primary" />
            <span className="font-semibold tracking-tight">Collected Parameters</span>
          </div>
          <ThemeToggle />
        </div>
      </header>
      <main className="flex-1 max-w-[1100px] w-full mx-auto px-6 py-10">{children}</main>
    </div>
  )

  // ---- gate -----------------------------------------------------------

  if (!review) {
    return shell(
      <form
        onSubmit={(e) => {
          e.preventDefault()
          load(adminCode.trim())
        }}
        className="max-w-[400px] mx-auto py-12"
      >
        <ShieldCheck className="size-9 text-primary mb-5" />
        <h1 className="text-2xl font-semibold tracking-tight mb-2">Review code</h1>
        <p className="text-muted-foreground text-sm mb-7">
          This is a different code from the one on the submission link.
        </p>

        <div className="space-y-2 mb-5">
          <Label htmlFor="admin">Code</Label>
          <Input
            id="admin"
            type="password"
            value={adminCode}
            onChange={(e) => setAdminCode(e.target.value)}
            autoComplete="off"
            autoFocus
            required
          />
        </div>

        {err && (
          <p className="text-sm text-destructive mb-5" role="alert">
            {err}
          </p>
        )}

        <Button type="submit" className="w-full" disabled={busy || !adminCode.trim()}>
          {busy && <Loader2 className="size-4 animate-spin" />}
          Open
        </Button>
      </form>,
    )
  }

  // ---- table ----------------------------------------------------------

  const allFields = review.sections.flatMap((s) => s.fields)

  return shell(
    <>
      <div className="flex items-end justify-between gap-4 mb-8 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight mb-1">
            {review.count} {review.count === 1 ? 'submission' : 'submissions'}
          </h1>
          <p className="text-muted-foreground text-sm">
            {review.field_count} parameters each. Click a row to see the answers.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => load(adminCode.trim())}
            disabled={busy}
          >
            {busy ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4" />
            )}
            Refresh
          </Button>
          <Button onClick={save} disabled={downloading || review.count === 0}>
            {downloading ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Download className="size-4" />
            )}
            Download CSV
          </Button>
        </div>
      </div>

      {err && (
        <p className="text-sm text-destructive mb-5" role="alert">
          {err}
        </p>
      )}

      {review.count === 0 ? (
        <div className="border rounded-lg py-20 text-center text-muted-foreground">
          <p className="text-sm">Nothing submitted yet.</p>
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/40">
              <tr className="text-left">
                <th className="w-9" />
                <th className="px-3 py-2.5 font-medium text-xs uppercase tracking-wider text-muted-foreground">
                  Code
                </th>
                <th className="px-3 py-2.5 font-medium text-xs uppercase tracking-wider text-muted-foreground">
                  Unknown
                </th>
                <th className="px-3 py-2.5 font-medium text-xs uppercase tracking-wider text-muted-foreground">
                  Submitted
                </th>
                <th className="px-3 py-2.5 font-medium text-xs uppercase tracking-wider text-muted-foreground">
                  Updated
                </th>
              </tr>
            </thead>
            <tbody>
              {review.submissions.map((s) => {
                const expanded = open === s.code
                const unknowns = countUnknown(s, allFields)

                return (
                  <Fragment key={s.code}>
                    <tr
                      onClick={() => setOpen(expanded ? null : s.code)}
                      className="border-t cursor-pointer hover:bg-muted/30"
                    >
                      <td className="pl-3 text-muted-foreground">
                        {expanded ? (
                          <ChevronDown className="size-4" />
                        ) : (
                          <ChevronRight className="size-4" />
                        )}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-[13px] font-medium">
                        {s.code}
                      </td>
                      <td className="px-3 py-2.5 tabular-nums text-muted-foreground">
                        {unknowns} / {allFields.length}
                      </td>
                      <td className="px-3 py-2.5 text-muted-foreground">
                        {when(s.created_at)}
                      </td>
                      <td className="px-3 py-2.5 text-muted-foreground">
                        {when(s.updated_at)}
                        {s.revision > 1 && (
                          <span className="ml-1.5 text-xs">
                            (rev {s.revision})
                          </span>
                        )}
                      </td>
                    </tr>

                    {expanded && (
                      <tr className="border-t bg-muted/20">
                        <td colSpan={5} className="px-5 py-5">
                          {review.sections.map((section) => (
                            <div key={section.section} className="mb-5 last:mb-0">
                              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                                {section.section}
                              </h3>
                              <dl className="grid gap-x-8 gap-y-1.5 sm:grid-cols-2">
                                {section.fields.map((f) => {
                                  const a = s.answers[f.key]
                                  return (
                                    <div
                                      key={f.key}
                                      className="flex justify-between gap-4 border-b border-border/40 py-1"
                                    >
                                      <dt className="text-muted-foreground">
                                        {f.label}
                                      </dt>
                                      <dd
                                        className={
                                          a?.unknown
                                            ? 'text-muted-foreground italic'
                                            : 'font-medium tabular-nums'
                                        }
                                      >
                                        {answerText(a)}
                                        {!a?.unknown && f.unit && (
                                          <span className="text-muted-foreground font-normal ml-1">
                                            {f.unit}
                                          </span>
                                        )}
                                      </dd>
                                    </div>
                                  )
                                })}
                              </dl>
                            </div>
                          ))}

                          {(s.answers._bmi || s.answers._whr || s.answers._pack_years) && (
                            <div className="mb-5">
                              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                                Calculated
                              </h3>
                              <dl className="grid gap-x-8 gap-y-1.5 sm:grid-cols-2">
                                {s.answers._bmi && (
                                  <div className="flex justify-between gap-4 border-b border-border/40 py-1">
                                    <dt className="text-muted-foreground">BMI</dt>
                                    <dd className="font-medium tabular-nums">
                                      {answerText(s.answers._bmi)}
                                      <span className="text-muted-foreground font-normal ml-1">
                                        kg/m²
                                      </span>
                                    </dd>
                                  </div>
                                )}
                                {s.answers._whr && (
                                  <div className="flex justify-between gap-4 border-b border-border/40 py-1">
                                    <dt className="text-muted-foreground">Waist-hip ratio</dt>
                                    <dd className="font-medium tabular-nums">
                                      {answerText(s.answers._whr)}
                                    </dd>
                                  </div>
                                )}
                                {s.answers._pack_years && (
                                  <div className="flex justify-between gap-4 border-b border-border/40 py-1">
                                    <dt className="text-muted-foreground">Pack-years</dt>
                                    <dd className="font-medium tabular-nums">
                                      {answerText(s.answers._pack_years)}
                                    </dd>
                                  </div>
                                )}
                              </dl>
                            </div>
                          )}

                          {s.answers._notes && (
                            <div>
                              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                                Notes
                              </h3>
                              <p className="text-sm">{answerText(s.answers._notes)}</p>
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </>,
  )
}
