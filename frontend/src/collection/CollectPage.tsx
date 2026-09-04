import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  CheckCircle2,
  ClipboardList,
  FileText,
  Loader2,
  ShieldCheck,
  User,
} from 'lucide-react'
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
// Two rules carried over from the desktop tool this replaces, both load-bearing:
//
//   1. Every parameter must be answered — a value, or an explicit "Don't know".
//      No healthy defaults, no silent blanks.
//   2. Submitting again under the same employee code corrects that record
//      rather than adding a second one.
//
// The access code arrives in the link as ?k=..., so an invited person clicks
// once and lands here. Typing it is the fallback for a link that lost its query
// string.
//
// A draft is kept in localStorage. Twenty-seven questions on a phone is long
// enough that one stray back-swipe losing everything is a real risk.

type Draft = Record<string, { value: string; unknown: boolean }>

const DRAFT_KEY = 'hhs-collect-draft'

function emptyDraft(schema: Schema): Draft {
  const draft: Draft = {}
  for (const section of schema.sections) {
    for (const field of section.fields) {
      draft[field.key] = { value: '', unknown: false }
    }
  }
  return draft
}

function loadDraft(schema: Schema): Draft {
  const fresh = emptyDraft(schema)
  try {
    const saved = JSON.parse(localStorage.getItem(DRAFT_KEY) ?? 'null')
    if (!saved || typeof saved !== 'object') return fresh
    // Only restore keys the current schema still has — a stale draft from
    // before a field was renamed must not resurrect it.
    for (const key of Object.keys(fresh)) {
      if (saved[key]) fresh[key] = saved[key]
    }
  } catch {
    // Private browsing, or a corrupt draft. Start clean rather than fail.
  }
  return fresh
}

function saveDraft(draft: Draft, name: string, code: string) {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({ ...draft, _name: { value: name, unknown: false }, _code: { value: code, unknown: false } }))
  } catch {
    // Storage full or blocked. The form still works; only resume is lost.
  }
}

function clearDraft() {
  try {
    localStorage.removeItem(DRAFT_KEY)
  } catch {
    /* nothing to do */
  }
}

/** Whether an earlier answer makes this field meaningless. */
function disabledBy(field: FieldDef, draft: Draft): string | null {
  const rule = field.depends_on
  if (!rule) return null

  const controlling = draft[rule.field]
  if (!controlling || controlling.unknown) return null

  const current = controlling.value.trim()
  if (current === '') return null

  const hit = rule.disabled_when.some((trigger) => {
    const a = Number(current)
    const b = Number(trigger)
    if (!Number.isNaN(a) && !Number.isNaN(b)) return a === b
    return current.toLowerCase() === String(trigger).toLowerCase()
  })

  return hit ? rule.field : null
}

export function CollectPage() {
  const [params] = useSearchParams()
  const codeFromLink = params.get('k')?.trim() ?? ''

  const [accessCode, setAccessCode] = useState(codeFromLink)
  const [checking, setChecking] = useState(codeFromLink !== '')
  const [schema, setSchema] = useState<Schema | null>(null)
  const [draft, setDraft] = useState<Draft>({})

  const [fullName, setFullName] = useState('')
  const [employeeCode, setEmployeeCode] = useState('')
  const [notes, setNotes] = useState('')

  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [done, setDone] = useState<{ created: boolean } | null>(null)

  const openSchema = (loaded: Schema) => {
    setSchema(loaded)
    const restored = loadDraft(loaded)
    setDraft(restored)
    try {
      const saved = JSON.parse(localStorage.getItem(DRAFT_KEY) ?? 'null')
      if (saved?._name?.value) setFullName(saved._name.value)
      if (saved?._code?.value) setEmployeeCode(saved._code.value)
    } catch {
      /* no draft to restore */
    }
  }

  // ---- link-supplied code ---------------------------------------------

  useEffect(() => {
    if (!codeFromLink) return
    let cancelled = false

    fetchSchema(codeFromLink)
      .then((loaded) => !cancelled && openSchema(loaded))
      .catch((e) => !cancelled && setErr(e instanceof Error ? e.message : String(e)))
      .finally(() => !cancelled && setChecking(false))

    return () => {
      cancelled = true
    }
  }, [codeFromLink])

  // ---- persist the draft ----------------------------------------------

  useEffect(() => {
    if (!schema || done) return
    saveDraft(draft, fullName, employeeCode)
  }, [draft, fullName, employeeCode, schema, done])

  // ---- progress --------------------------------------------------------

  const allFields = useMemo(
    () => (schema ? schema.sections.flatMap((s) => s.fields) : []),
    [schema],
  )

  const answered = useMemo(
    () =>
      allFields.filter((f) => {
        const entry = draft[f.key]
        if (!entry) return false
        return entry.unknown || entry.value.trim() !== '' || disabledBy(f, draft) !== null
      }).length,
    [allFields, draft],
  )

  // ---- actions ---------------------------------------------------------

  const unlock = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setErr(null)
    try {
      openSchema(await fetchSchema(accessCode.trim()))
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const send = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!schema) return

    setBusy(true)
    setErr(null)
    setFieldErrors({})

    const answers: Record<string, AnswerValue> = {}
    for (const field of allFields) {
      const entry = draft[field.key]
      const off = disabledBy(field, draft)

      if (off) {
        answers[field.key] = {
          value: field.depends_on!.value_when_disabled,
          unknown: false,
        }
      } else if (entry.unknown) {
        answers[field.key] = { value: null, unknown: true }
      } else {
        answers[field.key] = { value: entry.value, unknown: false }
      }
    }

    try {
      const result = await submit(accessCode.trim(), {
        full_name: fullName,
        employee_code: employeeCode,
        answers,
        notes,
      })
      clearDraft()
      setDone({ created: result.created })
      window.scrollTo({ top: 0 })
    } catch (e) {
      if (e instanceof CollectError && e.fieldErrors.length > 0) {
        const map: Record<string, string> = {}
        for (const fe of e.fieldErrors) map[fe.field] = fe.message
        setFieldErrors(map)
        setErr(
          `${e.fieldErrors.length} ${e.fieldErrors.length === 1 ? 'answer needs' : 'answers need'} attention.`,
        )
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

  const shell = (children: React.ReactNode, progress?: boolean) => (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b bg-card/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-[820px] mx-auto px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <ClipboardList className="size-5 text-primary" />
            <span className="font-semibold tracking-tight">Health Parameters</span>
          </div>
          <div className="flex items-center gap-4">
            {progress && schema && (
              <span className="text-xs text-muted-foreground tabular-nums hidden sm:inline">
                {answered} of {schema.field_count} answered
              </span>
            )}
            <ThemeToggle />
          </div>
        </div>
        {progress && schema && (
          <div className="h-0.5 bg-border">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${(answered / schema.field_count) * 100}%` }}
            />
          </div>
        )}
      </header>
      <main className="flex-1 max-w-[820px] w-full mx-auto px-6 py-10">{children}</main>
    </div>
  )

  // ---- done -----------------------------------------------------------

  if (done) {
    return shell(
      <div className="max-w-[520px] mx-auto text-center py-16">
        <CheckCircle2 className="size-12 text-primary mx-auto mb-5" />
        <h1 className="text-2xl font-semibold tracking-tight mb-2">
          {done.created ? 'Thank you' : 'Your answers were updated'}
        </h1>
        <p className="text-muted-foreground mb-8">
          {done.created
            ? 'Your answers have been recorded.'
            : 'Your earlier submission has been replaced with these answers.'}
        </p>
        <Button
          variant="outline"
          onClick={() => {
            setDone(null)
            if (schema) setDraft(emptyDraft(schema))
            setFullName('')
            setEmployeeCode('')
            setNotes('')
            clearDraft()
          }}
        >
          Fill in for someone else
        </Button>
      </div>,
    )
  }

  // ---- checking a link-supplied code ----------------------------------

  if (checking) {
    return shell(
      <div className="py-24 text-center text-muted-foreground">
        <Loader2 className="size-6 animate-spin mx-auto mb-3" />
        <p className="text-sm">Opening the form…</p>
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
          {codeFromLink
            ? 'That link did not work. Enter the current code, or ask for a fresh link.'
            : 'Your invitation link should open this form directly. If it did not, enter the code you were given.'}
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

  // ---- the form -------------------------------------------------------

  let lastGroup: string | null = null

  return shell(
    <form onSubmit={send} className="pb-20">
      <h1 className="text-2xl font-semibold tracking-tight mb-2">Health parameters</h1>
      <p className="text-muted-foreground text-sm mb-8 max-w-[62ch]">
        {schema.field_count} questions, around five minutes. Every one needs an
        answer — a value, or <span className="font-medium text-foreground">Don't know</span>.
        Your answers are saved on this device as you go, so you can close this and
        come back.
      </p>

      {/* identity */}
      <section className="mb-10 rounded-lg border bg-card p-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="full-name">Full name</Label>
            <Input
              id="full-name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="emp-code">Employee code</Label>
            <Input
              id="emp-code"
              value={employeeCode}
              onChange={(e) => setEmployeeCode(e.target.value)}
              placeholder="D220098"
              className="font-mono"
              required
            />
            <p className="text-xs text-muted-foreground">
              Filling this in again with the same code replaces your earlier answers.
            </p>
          </div>
        </div>
      </section>

      {schema.sections.map((section) => {
        const newGroup = section.group !== lastGroup
        lastGroup = section.group

        return (
          <div key={section.section}>
            {newGroup && (
              <div className="mb-6 mt-4 first:mt-0 flex gap-3 rounded-lg bg-muted/50 p-4">
                {section.group === 'self' ? (
                  <User className="size-4 mt-0.5 shrink-0 text-primary" />
                ) : (
                  <FileText className="size-4 mt-0.5 shrink-0 text-primary" />
                )}
                <div>
                  <h2 className="font-semibold text-sm mb-0.5">
                    {section.group === 'self' ? 'About you' : 'From your health report'}
                  </h2>
                  <p className="text-xs text-muted-foreground max-w-[60ch]">
                    {schema.groups[section.group]}
                  </p>
                </div>
              </div>
            )}

            <section className="mb-9">
              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-4 pb-2 border-b">
                {section.section}
              </h3>

              <div className="space-y-6">
                {section.fields.map((field) => {
                  const entry = draft[field.key]
                  const problem = fieldErrors[field.key]
                  const off = disabledBy(field, draft)
                  const offBecause = off ? allFields.find((f) => f.key === off) : null

                  return (
                    <div key={field.key} id={`field-${field.key}`}>
                      <div className="flex items-baseline justify-between gap-3 mb-1">
                        <Label htmlFor={field.key} className="text-[15px]">
                          {field.label}
                        </Label>
                        {field.unit && (
                          <span className="text-xs text-muted-foreground shrink-0">
                            {field.unit}
                          </span>
                        )}
                      </div>

                      <p className="text-[13px] text-muted-foreground mb-2.5 max-w-[64ch]">
                        {field.description}
                      </p>

                      {off ? (
                        <p className="text-[13px] rounded-md border border-dashed px-3 py-2 text-muted-foreground">
                          Not needed — you answered “{draft[off].value}” for{' '}
                          {offBecause?.label}.
                        </p>
                      ) : field.kind === 'choice' ? (
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
                        <div className="flex gap-2">
                          <Input
                            id={field.key}
                            type={field.kind === 'number' ? 'number' : 'text'}
                            step="any"
                            inputMode={field.kind === 'number' ? 'decimal' : undefined}
                            value={entry.unknown ? '' : entry.value}
                            disabled={entry.unknown}
                            placeholder={entry.unknown ? "Don't know" : undefined}
                            onChange={(e) => setValue(field.key, e.target.value)}
                            aria-invalid={problem ? true : undefined}
                          />
                          <Button
                            type="button"
                            variant={entry.unknown ? 'default' : 'outline'}
                            onClick={() => setUnknown(field.key, !entry.unknown)}
                            className="shrink-0"
                          >
                            Don't know
                          </Button>
                        </div>
                      )}

                      {problem && (
                        <p className="text-xs text-destructive mt-1.5" role="alert">
                          {problem}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            </section>
          </div>
        )
      })}

      <section className="mb-9">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-4 pb-2 border-b">
          Anything else
        </h3>
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="Optional — anything that did not fit the questions above."
        />
      </section>

      {err && (
        <p className="text-sm text-destructive mb-4" role="alert">
          {err}
        </p>
      )}

      <div className="flex items-center gap-4 sticky bottom-0 bg-background/95 backdrop-blur py-4 border-t">
        <Button type="submit" size="lg" disabled={busy}>
          {busy && <Loader2 className="size-4 animate-spin" />}
          Submit
        </Button>
        <span className="text-sm text-muted-foreground tabular-nums">
          {answered} of {schema.field_count} answered
        </span>
      </div>
    </form>,
    true,
  )
}
