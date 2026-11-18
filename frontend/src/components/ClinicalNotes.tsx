import { useEffect, useRef, useState } from 'react'
import { fetchNote, saveNote } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Loader2, StickyNote, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  patientId: string
  /** Encounter-level note from the intake payload, used only as a starting point. */
  initialNote?: string
}

/**
 * The clinician's note as a floating bubble in the bottom-right corner. Click
 * it to open the editor, click again (or Esc) to tuck it away.
 *
 * The note's state lives here, not in the panel, so closing the panel keeps an
 * unsaved edit; the bubble shows a dot until it is saved.
 */
export function ClinicalNotes({ patientId, initialNote }: Props) {
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState('')
  const [lastSaved, setLastSaved] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [savedAt, setSavedAt] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const textarea = useRef<HTMLTextAreaElement>(null)

  // Guards against a slow response for a previous patient overwriting the
  // note of the one now selected.
  const seq = useRef(0)

  useEffect(() => {
    if (!patientId) return
    const mine = ++seq.current
    setLoading(true)
    setErr(null)
    setSavedAt(null)

    fetchNote(patientId)
      .then((saved) => {
        if (seq.current !== mine) return
        // A saved review note wins; otherwise fall back to the intake note.
        const text = saved?.note ?? initialNote ?? ''
        setNote(text)
        setLastSaved(saved ? saved.note : text)
        setSavedAt(saved?.updated_at ?? null)
      })
      .catch((e) => {
        if (seq.current !== mine) return
        setNote(initialNote ?? '')
        setLastSaved(initialNote ?? '')
        setErr(`Could not load saved note: ${e}`)
      })
      .finally(() => {
        if (seq.current === mine) setLoading(false)
      })
  }, [patientId, initialNote])

  useEffect(() => {
    if (!open) return
    const el = textarea.current
    if (el) {
      el.focus()
      el.setSelectionRange(el.value.length, el.value.length)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const dirty = note !== lastSaved

  const save = async () => {
    setSaving(true)
    setErr(null)
    try {
      const saved = await saveNote(patientId, note)
      setLastSaved(saved.note)
      setSavedAt(saved.updated_at)
    } catch (e) {
      setErr(`Not saved: ${e}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed bottom-5 right-5 z-30 flex flex-col items-end gap-3">
      {open && (
        <section
          role="dialog"
          aria-label="Clinical notes"
          className="w-[24rem] max-w-[calc(100vw-2.5rem)] rounded-lg border bg-card shadow-xl overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-150"
        >
          <div className="px-4 py-2.5 border-b flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 card-title">
              <StickyNote className="h-4 w-4 text-primary" />
              Clinical Notes
            </div>
            <div className="flex items-center gap-1">
              {loading && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setOpen(false)}
                aria-label="Close notes"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="p-4 space-y-2.5">
            <Textarea
              ref={textarea}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add observations, follow-ups, or context for this patient…"
              rows={9}
              disabled={loading}
              className="text-sm bg-background resize-y min-h-40"
            />

            {err && <p className="text-xs text-destructive leading-snug">{err}</p>}

            <div className="flex items-center gap-2">
              <Button size="sm" onClick={save} disabled={saving || loading || !dirty}>
                {saving ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…
                  </>
                ) : (
                  'Save Note'
                )}
              </Button>
              <span className="text-xs text-muted-foreground">
                {dirty
                  ? 'Unsaved changes'
                  : savedAt && !err
                    ? `Saved ${new Date(savedAt).toLocaleString()}`
                    : ''}
              </span>
            </div>
          </div>
        </section>
      )}

      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={open ? 'Hide clinical notes' : 'Show clinical notes'}
        title={open ? 'Hide clinical notes' : 'Clinical notes'}
        className={cn(
          'relative flex h-12 items-center gap-2 rounded-full px-4 shadow-lg transition-colors cursor-pointer',
          'bg-primary text-primary-foreground hover:bg-primary/90',
          'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
        )}
      >
        {open ? <X className="h-5 w-5" /> : <StickyNote className="h-5 w-5" />}
        <span className="text-sm font-medium">Notes</span>
        {dirty && (
          <span
            className="absolute -top-0.5 -right-0.5 h-3 w-3 rounded-full bg-amber-400 ring-2 ring-background"
            aria-label="Unsaved changes"
          />
        )}
      </button>
    </div>
  )
}
