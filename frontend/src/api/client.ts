// Fetch wrapper for the backend. Vite proxy forwards /api -> :8000.
import type {
  Assessment,
  DashboardBundle,
  DuplicateVisitError,
  IntakeSchema,
  MonitoringData,
  SavedNote,
  SaveResult,
  Source,
  Submission,
  ValidationPayload,
} from '../types'

export async function fetchPatients(source: Source): Promise<string[]> {
  const res = await fetch(`/api/patients?source=${source}`)
  if (!res.ok) throw new Error(`patients: ${res.status} ${await res.text()}`)
  const data = await res.json()
  return data.patient_ids as string[]
}

export async function fetchDashboard(
  patientId: string,
  source: Source,
): Promise<DashboardBundle> {
  const res = await fetch(`/api/patients/${encodeURIComponent(patientId)}?source=${source}`)
  if (!res.ok) throw new Error(`dashboard: ${res.status} ${await res.text()}`)
  return res.json()
}

export async function postValidation(
  payload: ValidationPayload,
): Promise<{ status: string; validation: ValidationPayload }> {
  const res = await fetch('/api/validation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`validation: ${res.status} ${await res.text()}`)
  return res.json()
}

// --- Clinical review notes --------------------------------------------------

export async function fetchNote(patientId: string): Promise<SavedNote | null> {
  const res = await fetch(`/api/patients/${encodeURIComponent(patientId)}/note`)
  if (!res.ok) throw new Error(`note: ${res.status} ${await res.text()}`)
  const data = await res.json()
  return (data.note ?? null) as SavedNote | null
}

export async function saveNote(
  patientId: string,
  note: string,
  author = '',
): Promise<SavedNote> {
  const res = await fetch(`/api/patients/${encodeURIComponent(patientId)}/note`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note, author }),
  })
  if (!res.ok) throw new Error(`note: ${res.status} ${await res.text()}`)
  const data = await res.json()
  return data.note as SavedNote
}

// --- Monitoring / trends ----------------------------------------------------

// Resolves to null for patients with no saved encounters (all CSV patients).
export async function fetchMonitoring(patientId: string): Promise<MonitoringData | null> {
  const res = await fetch(`/api/patients/${encodeURIComponent(patientId)}/monitoring`)
  if (!res.ok) throw new Error(`monitoring: ${res.status} ${await res.text()}`)
  const data = await res.json()
  return (data.monitoring ?? null) as MonitoringData | null
}

// --- Intake -----------------------------------------------------------------

export async function fetchIntakeSchema(): Promise<IntakeSchema> {
  const res = await fetch('/api/intake/schema')
  if (!res.ok) throw new Error(`schema: ${res.status} ${await res.text()}`)
  return res.json()
}

export async function scoreSubmission(submission: Submission): Promise<Assessment> {
  const res = await fetch('/api/intake/score', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(submission),
  })
  if (!res.ok) throw new Error(`score: ${res.status} ${await res.text()}`)
  const data = await res.json()
  return data.assessment as Assessment
}

// Thrown on 409 so the form can offer "save anyway".
export class DuplicateVisitConflict extends Error {
  info: DuplicateVisitError

  constructor(info: DuplicateVisitError) {
    super(info.message)
    this.name = 'DuplicateVisitConflict'
    this.info = info
  }
}

export async function saveEncounter(submission: Submission): Promise<SaveResult> {
  const res = await fetch('/api/intake/encounters', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(submission),
  })

  if (res.status === 409) {
    const body = await res.json()
    throw new DuplicateVisitConflict(body.detail as DuplicateVisitError)
  }
  if (!res.ok) throw new Error(`save: ${res.status} ${await res.text()}`)
  return res.json()
}