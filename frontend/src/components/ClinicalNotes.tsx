import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { StickyNote } from 'lucide-react'

interface Props {
  patientId: string
  initialNote?: string
}

// TODO: wire save() to backend notes API when available.
// For now persists to localStorage keyed per patient.
export function ClinicalNotes({ patientId, initialNote }: Props) {
  const storageKey = `hhs-note-${patientId}`
  const [note, setNote] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const local = localStorage.getItem(storageKey)
    setNote(initialNote?.trim() ? initialNote : (local ?? ''))
    setSaved(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId, initialNote])

  const save = () => {
    localStorage.setItem(storageKey, note)
    setSaved(true)
  }

  return (
    <div className="rounded-xl border bg-card shadow-xs overflow-hidden">
      <div className="p-3 border-b">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <StickyNote className="h-3.5 w-3.5" />
          Clinical Notes
        </div>
      </div>
      <div className="p-3 space-y-2.5">
        <Textarea
          value={note}
          onChange={(e) => {
            setNote(e.target.value)
            setSaved(false)
          }}
          placeholder="Add observations, follow-ups, or context for this patient…"
          rows={12}
          className="text-sm bg-background resize-y min-h-48"
        />
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={save}>
            Save Note
          </Button>
          {saved && (
            <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
              Saved.
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
