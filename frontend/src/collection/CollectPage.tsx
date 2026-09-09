import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Check,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Info,
  Loader2,
  ShieldCheck,
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
  type Accent,
  type AnswerValue,
  type FieldDef,
  type Schema,
  type SectionDef,
} from './api'

// The additional-parameter collection form.
//
// Sections are collapsed accordions rather than one long scroll: twenty-eight
// questions presented at once reads as a wall, and the three optional sections
// in particular should not look like work until someone opens them. Required
// sections start open, optional ones closed.
//
// Two rules carried over from the desktop tool this replaces:
//
//   1. A required answer is a value or an explicit "Don't know" — no silent
//      blanks. Optional sections may be left alone entirely; the server stores
//      those the same way an explicit Unknown would be stored.
//   2. Submitting again under the same code corrects that record rather than
//      adding a second one.
//
// Identity is one code, mailed to the participant. No name is asked for.

type Draft = Record<string, { value: string; unknown: boolean }>

const DRAFT_KEY = 'hhs-collect-draft'

// Static class strings per accent: Tailwind cannot see a class assembled at
// runtime, so these have to be written out rather than interpolated.
const ACCENTS: Record<Accent, { bar: string; dot: string; text: string; soft: string }> = {
  sky:     { bar: 'bg-sky-500',     dot: 'bg-sky-500',     text: 'text-sky-700 dark:text-sky-300',         soft: 'bg-sky-500/5' },
  amber:   { bar: 'bg-amber-500',   dot: 'bg-amber-500',   text: 'text-amber-700 dark:text-amber-300',     soft: 'bg-amber-500/5' },
  emerald: { bar: 'bg-emerald-500', dot: 'bg-emerald-500', text: 'text-emerald-700 dark:text-emerald-300', soft: 'bg-emerald-500/5' },
  violet:  { bar: 'bg-violet-500',  dot: 'bg-violet-500',  text: 'text-violet-700 dark:text-violet-300',   soft: 'bg-violet-500/5' },
  rose:    { bar: 'bg-rose-500',    dot: 'bg-rose-500',    text: 'text-rose-700 dark:text-rose-300',       soft: 'bg-rose-500/5' },
  indigo:  { bar: 'bg-indigo-500',  dot: 'bg-indigo-500',  text: 'text-indigo-700 dark:text-indigo-300',   soft: 'bg-indigo-500/5' },
  teal:    { bar: 'bg-teal-500',    dot: 'bg-teal-500',    text: 'text-teal-700 dark:text-teal-300',       soft: 'bg-teal-500/5' },
}

function emptyDraft(schema: Schema): Draft {
  const draft: Draft = {}
  for (const section of schema.sections) {
    for (const field of section.fields) draft[field.key] = { value: '', unknown: false }
  }
  return draft
}

function loadDraft(schema: Schema): { draft: Draft; code: string } {
  const draft = emptyDraft(schema)
  let code = ''
  try {
    const saved = JSON.parse(localStorage.getItem(DRAFT_KEY) ?? 'null')
    if (saved && typeof saved === 'object') {
      // Only restore keys the schema still has, so a stale draft cannot
      // resurrect a field that has since been renamed.
      for (const key of Object.keys(draft)) if (saved[key]) draft[key] = saved[key]
      if (typeof saved._code?.value === 'string') code = saved._code.value
    }
  } catch {
    // Private browsing or a corrupt draft. Start clean rather than fail.
  }
  return { draft, code }
}

function saveDraft(draft: Draft, code: string) {
  try {
    localStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({ ...draft, _code: { value: code, unknown: false } }),
    )
  } catch {
    // Storage blocked or full. The form still works; only resume is lost.
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

function isAnswered(field: FieldDef, draft: Draft): boolean {
  if (disabledBy(field, draft)) return true
  const entry = draft[field.key]
  return Boolean(entry) && (entry.unknown || entry.value.trim() !== '')
}

export function CollectPage() {
  const [params] = useSearchParams()
  const codeFromLink = params.get('k')?.trim() ?? ''

  const [accessCode, setAccessCode] = useState(codeFromLink)
  const [checking, setChecking] = useState(codeFromLink !== '')
  const [schema, setSchema] = useState<Schema | null>(null)
  const [draft, setDraft] = useState<Draft>({})
  const [open, setOpen] = useState<Record<string, boolean>>({})

  const [code, setCode] = useState('')
  const [notes, setNotes] = useState('')

  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [done, setDone] = useState<{ created: boolean } | null>(null)

  const openSchema = (loaded: Schema) => {
    setSchema(loaded)
    const restored = loadDraft(loaded)
    setDraft(restored.draft)
    if (restored.code) setCode(restored.code)
    // Required sections open, optional closed — the point of collapsing is
    // that the optional half should not look like work until it is wanted.
    setOpen(
      Object.fromEntries(loaded.sections.map((s) => [s.section, !s.optional])),
    )
  }

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

  useEffect(() => {
    if (!schema || done) return
    saveDraft(draft, code)
  }, [draft, code, schema, done])

  const requiredFields = useMemo(
    () =>
      schema
        ? schema.sections.filter((s) => !s.optional).flatMap((s) => s.fields)
        : [],
    [schema],
  )

  const requiredAnswered = useMemo(
    () => requiredFields.filter((f) => isAnswered(f, draft)).length,
    [requiredFields, draft],
  )

  const allFields = useMemo(
    () => (schema ? schema.sections.flatMap((s) => s.fields) : []),
    [schema],
  )

  const setValue = (key: string, value: string) =>
    setDraft((d) => ({ ...d, [key]: { value, unknown: false } }))

  const setUnknown = (key: string, unknown: boolean) =>
    setDraft((d) => ({ ...d, [key]: { value: unknown ? '' : d[key].value, unknown } }))

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
        answers[field.key] = { value: field.depends_on!.value_when_disabled, unknown: false }
      } else if (entry.unknown) {
        answers[field.key] = { value: null, unknown: true }
      } else {
        answers[field.key] = { value: entry.value, unknown: false }
      }
    }

    try {
      const result = await submit(accessCode.trim(), { code, answers, notes })
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
        // Open whichever sections hold a problem, then jump to the first.
        const bad = new Set(
          e.fieldErrors
            .map((fe) => allFields.find((f) => f.key === fe.field)?.section)
            .filter(Boolean) as string[],
        )
        setOpen((o) => ({ ...o, ...Object.fromEntries([...bad].map((s) => [s, true])) }))
        setTimeout(
          () =>
            document
              .getElementById(`field-${e.fieldErrors[0].field}`)
              ?.scrollIntoView({ block: 'center', behavior: 'smooth' }),
          80,
        )
      } else {
        setErr(e instanceof Error ? e.message : String(e))
      }
    } finally {
      setBusy(false)
    }
  }

  // ---- chrome ---------------------------------------------------------

  const shell = (children: React.ReactNode, progress?: boolean) => (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b bg-card/85 backdrop-blur sticky top-0 z-20">
        <div className="max-w-[760px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <ClipboardList className="size-5 text-primary" />
            <span className="font-semibold tracking-tight">Health Parameters</span>
          </div>
          <div className="flex items-center gap-4">
            {progress && schema && (
              <span className="text-xs text-muted-foreground tabular-nums hidden sm:inline">
                {requiredAnswered} of {schema.required_count} required
              </span>
            )}
            <ThemeToggle />
          </div>
        </div>
        {progress && schema && (
          <div className="h-0.5 bg-border">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${(requiredAnswered / schema.required_count) * 100}%` }}
            />
          </div>
        )}
      </header>
      <main className="flex-1 max-w-[760px] w-full mx-auto px-5 py-9">{children}</main>
    </div>
  )

  if (done) {
    return shell(
      <div className="max-w-[480px] mx-auto text-center py-16">
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
            if (schema) openSchema(schema)
            setCode('')
            setNotes('')
            clearDraft()
          }}
        >
          Fill in again
        </Button>
      </div>,
    )
  }

  if (checking) {
    return shell(
      <div className="py-24 text-center text-muted-foreground">
        <Loader2 className="size-6 animate-spin mx-auto mb-3" />
        <p className="text-sm">Opening the form…</p>
      </div>,
    )
  }

  if (!schema) {
    return shell(
      <form onSubmit={unlock} className="max-w-[380px] mx-auto py-12">
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

  // ---- one field ------------------------------------------------------

  const renderField = (field: FieldDef) => {
    const entry = draft[field.key]
    const problem = fieldErrors[field.key]
    const off = disabledBy(field, draft)
    const offBecause = off ? allFields.find((f) => f.key === off) : null

    return (
      <div key={field.key} id={`field-${field.key}`}>
        <Label htmlFor={field.key} className="text-[14.5px]">
          {field.label}
        </Label>
        <p className="text-[12.5px] text-muted-foreground mt-0.5 mb-2 max-w-[58ch]">
          {field.description}
        </p>

        {off ? (
          <p className="text-[12.5px] rounded-md border border-dashed px-3 py-1.5 text-muted-foreground inline-block">
            Not needed — you answered “{draft[off].value}” for {offBecause?.label}.
          </p>
        ) : field.kind === 'choice' ? (
          <select
            id={field.key}
            value={entry.value}
            onChange={(e) => setValue(field.key, e.target.value)}
            className="h-9 w-full max-w-[260px] rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            <option value="">Select…</option>
            {field.choices?.map((choice) => (
              <option key={choice} value={choice}>
                {choice}
              </option>
            ))}
          </select>
        ) : (
          <div className="flex items-center gap-2 flex-wrap">
            {/* Numbers are three or four digits; a full-width box for "170"
                reads as though more is expected. */}
            <div
              className={`flex items-center gap-1.5 ${
                field.kind === 'number' ? 'w-[128px]' : 'w-full max-w-[420px]'
              }`}
            >
              <Input
                id={field.key}
                type={field.kind === 'number' ? 'number' : 'text'}
                step="any"
                inputMode={field.kind === 'number' ? 'decimal' : undefined}
                value={entry.unknown ? '' : entry.value}
                disabled={entry.unknown}
                placeholder={entry.unknown ? '—' : field.placeholder}
                onChange={(e) => setValue(field.key, e.target.value)}
                aria-invalid={problem ? true : undefined}
                className={field.kind === 'number' ? 'tabular-nums' : ''}
              />
            </div>
            {field.unit && (
              <span className="text-xs text-muted-foreground shrink-0">{field.unit}</span>
            )}
            <Button
              type="button"
              size="sm"
              variant={entry.unknown ? 'default' : 'outline'}
              onClick={() => setUnknown(field.key, !entry.unknown)}
              className="shrink-0 ml-auto"
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
  }

  // ---- one section ----------------------------------------------------

  const renderSection = (section: SectionDef) => {
    const a = ACCENTS[section.accent]
    const expanded = open[section.section] ?? false
    const answered = section.fields.filter((f) => isAnswered(f, draft)).length
    const complete = answered === section.fields.length
    const hasProblem = section.fields.some((f) => fieldErrors[f.key])

    return (
      <section
        key={section.section}
        className={`rounded-lg border overflow-hidden ${
          hasProblem ? 'border-destructive/50' : ''
        }`}
      >
        <button
          type="button"
          onClick={() => setOpen((o) => ({ ...o, [section.section]: !expanded }))}
          aria-expanded={expanded}
          className="w-full flex items-stretch text-left hover:bg-muted/30 transition-colors"
        >
          <span className={`w-1 shrink-0 ${a.bar}`} aria-hidden />
          <span className="flex-1 px-4 py-3.5 flex items-center gap-3 min-w-0">
            <span className="flex-1 min-w-0">
              <span className="flex items-center gap-2 flex-wrap">
                <span className="font-medium">{section.section}</span>
                {section.optional && (
                  <span className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground border rounded px-1.5 py-0.5">
                    Optional
                  </span>
                )}
                {complete && !section.optional && (
                  <Check className={`size-3.5 ${a.text}`} aria-label="complete" />
                )}
              </span>
              <span className="block text-xs text-muted-foreground mt-0.5 truncate">
                {answered} of {section.fields.length} answered
              </span>
            </span>
            <ChevronDown
              className={`size-4 shrink-0 text-muted-foreground transition-transform ${
                expanded ? 'rotate-180' : ''
              }`}
            />
          </span>
        </button>

        {expanded && (
          <div className="border-t">
            <div className={`px-4 py-3 flex gap-2.5 ${a.soft}`}>
              <Info className={`size-3.5 mt-0.5 shrink-0 ${a.text}`} />
              <p className="text-[12.5px] text-muted-foreground max-w-[62ch]">
                {section.info}
              </p>
            </div>
            <div className="px-4 py-5 space-y-6">{section.fields.map(renderField)}</div>
          </div>
        )}
      </section>
    )
  }

  // ---- the form -------------------------------------------------------

  let lastGroup: string | null = null

  return shell(
    <form onSubmit={send} className="pb-20">
      <h1 className="text-2xl font-semibold tracking-tight mb-2">Health parameters</h1>
      <p className="text-muted-foreground text-sm mb-7 max-w-[62ch]">
        {schema.required_count} questions to answer, plus{' '}
        {schema.field_count - schema.required_count} optional ones you can skip. Open a
        section to fill it in. Your answers are saved on this device as you go, so you
        can close this and come back.
      </p>

      <div className="rounded-lg border bg-card p-5 mb-7">
        <Label htmlFor="code">Your code</Label>
        <p className="text-[12.5px] text-muted-foreground mt-0.5 mb-2">
          The code from your invitation email. Filling this form in again with the same
          code replaces your earlier answers rather than adding a second entry.
        </p>
        <Input
          id="code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="D220098"
          className="font-mono w-[180px]"
          autoComplete="off"
          required
        />
      </div>

      <div className="space-y-3">
        {schema.sections.map((section) => {
          const newGroup = section.group !== lastGroup
          lastGroup = section.group

          return (
            <div key={section.section} className="space-y-3">
              {newGroup && (
                <h2 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground pt-4 first:pt-0">
                  {section.group === 'self' ? 'About you' : 'From your health report'}
                  <span className="block font-normal normal-case tracking-normal text-xs mt-1 max-w-[60ch]">
                    {schema.groups[section.group]}
                  </span>
                </h2>
              )}
              {renderSection(section)}
            </div>
          )
        })}
      </div>

      <div className="mt-7">
        <Label htmlFor="notes">Anything else</Label>
        <p className="text-[12.5px] text-muted-foreground mt-0.5 mb-2">
          Optional — anything that did not fit the questions above.
        </p>
        <Textarea
          id="notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
        />
      </div>

      {err && (
        <p className="text-sm text-destructive mt-5" role="alert">
          {err}
        </p>
      )}

      <div className="flex items-center gap-4 sticky bottom-0 bg-background/95 backdrop-blur py-4 mt-6 border-t">
        <Button type="submit" size="lg" disabled={busy}>
          {busy && <Loader2 className="size-4 animate-spin" />}
          Submit
        </Button>
        <span className="text-sm text-muted-foreground tabular-nums">
          {requiredAnswered} of {schema.required_count} required answered
        </span>
      </div>
    </form>,
    true,
  )
}
