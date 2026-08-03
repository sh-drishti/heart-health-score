import { useEffect, useRef, useState } from 'react'
import { fetchNote, saveNote } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Loader2, StickyNote } from 'lucide-react'

interface Props {
  patientId: string
  /** Encounter-level note from the intake payload, used only as a starting point. */
  initialNote?: string
}

export function ClinicalNotes({ patientId, initialNote }: Props) {
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [savedAt, setSavedAt] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

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
        setNote(saved?.note ?? initialNote ?? '')
        setSavedAt(saved?.updated_at ?? null)
      })
      .catch((e) => {
        if (seq.current !== mine) return
        setNote(initialNote ?? '')
        setErr(`Could not load saved note: ${e}`)
      })
      .finally(() => {
        if (seq.current === mine) setLoading(false)
      })
  }, [patientId, initialNote])

  const save = async () => {
    setSaving(true)
    setErr(null)
    try {
      const saved = await saveNote(patientId, note)
      setSavedAt(saved.updated_at)
    } catch (e) {
      setErr(`Not saved: ${e}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-xl border bg-card shadow-xs overflow-hidden">
      <div className="p-3 border-b flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <StickyNote className="h-3.5 w-3.5" />
          Clinical Notes
        </div>
        {loading && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
      </div>
      <div className="p-3 space-y-2.5">
        <Textarea
          value={note}
          onChange={(e) => {
            setNote(e.target.value)
            setSavedAt(null)
          }}
          placeholder="Add observations, follow-ups, or context for this patient…"
          rows={12}
          disabled={loading}
          className="text-sm bg-background resize-y min-h-48"
        />

        {err && (
          <p className="text-xs text-destructive leading-snug">{err}</p>
        )}

        <div className="flex items-center gap-2">
          <Button size="sm" onClick={save} disabled={saving || loading}>
            {saving ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…
              </>
            ) : (
              'Save Note'
            )}
          </Button>
          {savedAt && !err && (
            <span className="text-xs text-muted-foreground">
              Saved {new Date(savedAt).toLocaleString()}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
