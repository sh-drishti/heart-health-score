// Client for the additional-parameter collection programme.
//
// Deliberately does NOT go through src/api/client.ts. That client attaches a
// bearer token and, on a 401, tries to refresh and then bounces to /login —
// all correct for the clinical app and all wrong here, where the person filling
// in the form has no account and a 401 means "wrong access code", not "session
// expired".
//
// Temporary, like the rest of this directory: delete src/collection/ to remove.

import { API_BASE } from '@/api/config'

const BASE = `${API_BASE}/api/collect`

/** A field is disabled when an earlier answer makes it meaningless — pack-years
 *  for someone who has never smoked. The server enforces this too; the browser
 *  is not the authority. */
export interface DependsOn {
  field: string
  disabled_when: (string | number)[]
  value_when_disabled: string | number
}

export interface FieldDef {
  key: string
  label: string
  section: string
  kind: 'number' | 'choice' | 'text'
  unit: string
  description: string
  /** 'self' — answerable from your own knowledge. 'report' — copied off a lab
   *  or scan result. */
  group: 'self' | 'report'
  choices?: string[]
  min?: number
  max?: number
  depends_on?: DependsOn
}

export interface SectionDef {
  section: string
  group: 'self' | 'report'
  fields: FieldDef[]
}

export interface Schema {
  sections: SectionDef[]
  groups: Record<string, string>
  field_count: number
}

export interface FieldError {
  field: string
  message: string
}

export class CollectError extends Error {
  status: number
  fieldErrors: FieldError[]

  constructor(status: number, message: string, fieldErrors: FieldError[] = []) {
    super(message)
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

async function parseError(res: Response): Promise<CollectError> {
  let detail: unknown = null
  try {
    detail = (await res.json())?.detail
  } catch {
    // A proxy error page, not JSON. Fall through to the status-based message.
  }

  if (detail && typeof detail === 'object' && 'errors' in detail) {
    const d = detail as { message?: string; errors?: FieldError[] }
    return new CollectError(
      res.status,
      d.message ?? 'Some parameters need attention.',
      d.errors ?? [],
    )
  }

  if (typeof detail === 'string') return new CollectError(res.status, detail)

  if (res.status === 401) return new CollectError(401, 'Wrong access code.')
  if (res.status === 503) return new CollectError(503, 'Collection is not open yet.')
  return new CollectError(res.status, 'Something went wrong. Please try again.')
}

export async function fetchSchema(accessCode: string): Promise<Schema> {
  const res = await fetch(`${BASE}/schema`, {
    headers: { 'X-Collection-Code': accessCode },
  })
  if (!res.ok) throw await parseError(res)
  return res.json()
}

export interface AnswerValue {
  value: string | number | null
  unknown: boolean
}

export interface SubmissionResult {
  employee_code: string
  created: boolean
  updated_at: string
}

export async function submit(
  accessCode: string,
  body: {
    full_name: string
    employee_code: string
    answers: Record<string, AnswerValue>
    notes: string
  },
): Promise<SubmissionResult> {
  const res = await fetch(`${BASE}/submissions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Collection-Code': accessCode,
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw await parseError(res)
  return res.json()
}


// ---- review (separate code) -------------------------------------------------

export interface StoredAnswer {
  value: string | number | null
  unknown: boolean
}

export interface Submission {
  employee_code: string
  full_name: string
  revision: number
  created_at: string
  updated_at: string
  answers: Record<string, StoredAnswer>
}

export interface Review extends Schema {
  count: number
  submissions: Submission[]
}

export async function fetchSubmissions(adminCode: string): Promise<Review> {
  const res = await fetch(`${BASE}/submissions`, {
    headers: { 'X-Admin-Code': adminCode },
  })
  if (!res.ok) throw await parseError(res)
  return res.json()
}

/** Downloads the CSV. The code travels in a header, so this cannot be a plain
 *  link — fetch it, then hand the browser a blob to save. */
export async function downloadCsv(adminCode: string): Promise<void> {
  const res = await fetch(`${BASE}/submissions.csv`, {
    headers: { 'X-Admin-Code': adminCode },
  })
  if (!res.ok) throw await parseError(res)

  const url = URL.createObjectURL(await res.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = `hhs-parameters-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
