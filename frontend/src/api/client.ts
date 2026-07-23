// Fetch wrapper for the backend. Vite proxy forwards /api -> :8000.
import type { DashboardBundle, Source, ValidationPayload } from '../types'

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