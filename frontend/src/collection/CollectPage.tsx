import { useState } from 'react'
import { CheckCircle2, ClipboardList, Loader2, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ThemeToggle } from '@/components/ThemeToggle'
import {
  CollectError,
  fetchSchema,
  submit,
  type AnswerValue,
  type FieldDef,
  type Schema,
} from './api'

// The additional-parameter collection form.
//
// Ported from a Tkinter desktop tool that wrote to a local CSV. Two rules from
// that tool are load-bearing and kept exactly:
//
//   1. Every parameter must be answered — a value, or an explicit Unknown.
//      There are no healthy defaults and no silent blanks.
//   2. Submitting again with the same employee code corrects the earlier
//      record rather than adding a second one.
//
// The access code is asked for first, before anyone fills in 25 fields, so a
// wrong code fails in two seconds rather than after ten minutes of typing.

type Draft = Record<string, { value: string; unknown: boolean }>

function emptyDraft(schema: Schema): Draft {
  const draft: Draft = {}
  for (const section of schema.sections) {
    for (const field of section.fields) {
      draft[field.key] = { value: '', unknown: false }
    }
  }
  return draft
}

function fieldHint(field: FieldDef): string {
  if (field.kind === 'number' && field.min !== undefined) {
    return field.unit
      ? `${field.min}–${field.max} ${field.unit}`
      : `${field.min}–${field.max}`
  }
  return field.unit
}

export function CollectPage() {
  const [accessCode, setAccessCode] = useState('')
  const [schema, setSchema] = useState<Schema | null>(null)
  const [draft, setDraft] = useState<Draft>({})

  const [fullName, setFullName] = useState('')
  const [employeeCode, setEmployeeCode] = useState('')
  const [notes, setNotes] = useState('')

  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [done, setDone] = useState<{ created: boolean } | null>(null)

  // ---- gate -----------------------------------------------------------

  const unlock = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setErr(null)
    try {
      const loaded = await fetchSchema(accessCode.trim())
      setSchema(loaded)
      setDraft(emptyDraft(loaded))
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  // ---- submit ---------------------------------------------------------

  const send = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!schema) return

    setBusy(true)
    setErr(null)
    setFieldErrors({})

    const answers: Record<string, AnswerValue> = {}
    for (const [key, entry] of Object.entries(draft)) {
      answers[key] = entry.unknown
        ? { value: null, unknown: true }
        : { value: entry.value, unknown: false }
    }

    try {
      const result = await submit(accessCode.trim(), {
        full_name: fullName,
        employee_code: employeeCode,
        answers,
        notes,
      })
      setDone({ created: result.created })
      window.scrollTo({ top: 0 })
    } catch (e) {
      if (e instanceof CollectError && e.fieldErrors.length > 0) {
        const map: Record<string, string> = {}
        for (const fe of e.fieldErrors) map[fe.field] = fe.message
        setFieldErrors(map)
        setErr(`${e.fieldErrors.length} parameter(s) need attention.`)
        // Take them to the first problem rather than leaving them to hunt.
        document
          .getElementById(`field-${e.fieldErrors[0].field}`)
          ?.scrollIntoView({ block: 'center', behavior: 'smooth' })
      } else {
        setErr(e instanceof Error ? e.message : String(e))
      }
    } finally {
      setBusy(false)
    }
  }

  const setValue = (key: string, value: string) =>
    setDraft((d) => ({ ...d, [key]: { value, unknown: false } }))

  const setUnknown = (key: string, unknown: boolean) =>
    setDraft((d) => ({ ...d, [key]: { value: unknown ? '' : d[key].value, unknown } }))

  // ---- chrome ---------------------------------------------------------

  const shell = (children: React.ReactNode) => (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b bg-card/80 backdrop-blur">
        <div className="max-w-[900px] mx-auto px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <ClipboardList className="size-5 text-primary" />
            <span className="font-semibold tracking-tight">
              Additional Parameter Collection
            </span>
          </div>
          <ThemeToggle />
        </div>
      </header>
      <main className="flex-1 max-w-[900px] w-full mx-auto px-6 py-10">{children}</main>
    </div>
  )

  // ---- done -----------------------------------------------------------

  if (done) {
    return shell(
      <div className="max-w-[520px] mx-auto text-center py-12">
        <CheckCircle2 className="size-12 text-primary mx-auto mb-5" />
        <h1 className="text-2xl font-semibold tracking-tight mb-2">
          {done.created ? 'Submitted' : 'Record updated'}
        </h1>
        <p className="text-muted-foreground mb-8">
          {done.created
            ? 'Your parameters have been recorded. Thank you.'
            : 'Your earlier submission has been replaced with these answers.'}
        </p>
        <Button
          variant="outline"
          onClick={() => {
            setDone(null)
            setDraft(schema ? emptyDraft(schema) : {})
            setFullName('')
            setEmployeeCode('')
            setNotes('')
          }}
        >
          Submit for someone else
        </Button>
      </div>,
    )
  }

  // ---- gate -----------------------------------------------------------

  if (!schema) {
    return shell(
      <form onSubmit={unlock} className="max-w-[400px] mx-auto py-12">
        <ShieldCheck className="size-9 text-primary mb-5" />
        <h1 className="text-2xl font-semibold tracking-tight mb-2">Access code</h1>
        <p className="text-muted-foreground text-sm mb-7">
          Enter the code you were given. It was sent with your invitation to this
          collection round.
        </p>

        <div className="space-y-2 mb-5">
          <Label htmlFor="access">Code</Label>
          <Input
            id="access"
            value={accessCode}
            onChange={(e) => setAccessCode(e.target.value)}
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

        <Button type="submit" className="w-full" disabled={busy || !accessCode.trim()}>
          {busy && <Loader2 className="size-4 animate-spin" />}
          Continue
        </Button>
      </form>,
    )
  }

  // ---- form -----------------------------------------------------------

  return shell(
    <form onSubmit={send} className="pb-16">
      <h1 className="text-2xl font-semibold tracking-tight mb-1.5">
        Additional parameters
      </h1>
      <p className="text-muted-foreground text-sm mb-9 max-w-[62ch]">
        {schema.field_count} parameters. Every one must be answered — enter a value,
        or mark it <span className="font-medium text-foreground">Unknown</span>. If
        you submit again with the same employee code, this record is corrected
        rather than duplicated.
      </p>

      {/* identity */}
      <section className="mb-10">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-4">
          About you
        </h2>
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="full-name">Full name</Label>
            <Input
              id="full-name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="emp-code">Company employee code</Label>
            <Input
              id="emp-code"
              value={employeeCode}
              onChange={(e) => setEmployeeCode(e.target.value)}
              required
            />
          </div>
        </div>
      </section>

      {/* parameters */}
      {schema.sections.map((section) => (
        <section key={section.section} className="mb-10">
          <h2 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-4 pb-2 border-b">
            {section.section}
          </h2>

          <div className="grid gap-6 sm:grid-cols-2">
            {section.fields.map((field) => {
              const entry = draft[field.key]
              const problem = fieldErrors[field.key]
              const hint = fieldHint(field)

              return (
                <div key={field.key} id={`field-${field.key}`} className="space-y-2">
                  <div className="flex items-baseline justify-between gap-3">
                    <Label htmlFor={field.key}>{field.label}</Label>
                    {hint && (
                      <span className="text-[11px] text-muted-foreground tabular-nums">
                        {hint}
                      </span>
                    )}
                  </div>

                  {field.kind === 'choice' ? (
                    <select
                      id={field.key}
                      value={entry.value}
                      onChange={(e) => setValue(field.key, e.target.value)}
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
                    >
                      <option value="">Select…</option>
                      {field.choices?.map((choice) => (
                        <option key={choice} value={choice}>
                          {choice}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <>
                      <Input
                        id={field.key}
                        type={field.kind === 'number' ? 'number' : 'text'}
                        step="any"
                        value={entry.value}
                        disabled={entry.unknown}
                        onChange={(e) => setValue(field.key, e.target.value)}
                        aria-invalid={problem ? true : undefined}
                      />
                      <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer w-fit">
                        <input
                          type="checkbox"
                          checked={entry.unknown}
                          onChange={(e) => setUnknown(field.key, e.target.checked)}
                          className="size-3.5 accent-primary"
                        />
                        Unknown
                      </label>
                    </>
                  )}

                  {problem && (
                    <p className="text-xs text-destructive" role="alert">
                      {problem}
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      ))}

      {/* notes */}
      <section className="mb-10">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-4 pb-2 border-b">
          Anything else
        </h2>
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="Optional — context that does not fit the fields above."
        />
      </section>

      {err && (
        <p className="text-sm text-destructive mb-5" role="alert">
          {err}
        </p>
      )}

      <Button type="submit" size="lg" disabled={busy}>
        {busy && <Loader2 className="size-4 animate-spin" />}
        Submit parameters
      </Button>
    </form>,
  )
}
