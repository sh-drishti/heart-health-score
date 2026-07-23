import { useMemo, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Search, Users } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  patientIds: string[]
  selectedPatient: string
  onSelect: (patientId: string) => void
}

export function PatientDirectory({ patientIds, selectedPatient, onSelect }: Props) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return patientIds
    return patientIds.filter((id) => id.toLowerCase().includes(q))
  }, [patientIds, query])

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-4 pb-3 space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <Users className="h-3.5 w-3.5" />
          Patients
          <span className="ml-auto tabular-nums font-normal">{patientIds.length}</span>
        </div>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter patients…"
            className="pl-8 h-8 text-sm bg-background"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {filtered.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-6">
            No patients match “{query}”.
          </p>
        ) : (
          filtered.map((id) => (
            <button
              key={id}
              onClick={() => onSelect(id)}
              className={cn(
                'w-full text-left px-3 py-1.5 rounded-md text-sm font-medium transition-colors cursor-pointer mb-0.5',
                id === selectedPatient
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-foreground hover:bg-muted',
              )}
            >
              {id}
            </button>
          ))
        )}
      </div>
    </div>
  )
}
