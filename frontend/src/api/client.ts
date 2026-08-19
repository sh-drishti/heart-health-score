// Fetch wrapper for the backend. Vite proxy forwards /api -> :8000.
//
// Every call goes through request(), which attaches the bearer token and, on a
// 401, refreshes once and retries. Callers never see an expired token.
import { apiUrl } from './config'
import {
  clearSession,
  endSession,
  getAccessToken,
  refreshSession,
  setSession,
} from './session'
import type {
  Assessment,
  AuthUser,
  DashboardBundle,
  DuplicateVisitError,
  IntakePrefill,
  IntakeSchema,
  MonitoringData,
  Role,
  SavedNote,
  SaveResult,
  Source,
  Submission,
  TokenPair,
  ValidationPayload,
  SavedValidation,
} from '../types'

/** A request the server refused. `status` lets callers branch on 401/403/404. */
export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(label: string, status: number, detail: unknown) {
    const text =
      typeof detail === 'string' ? detail : (detail as { message?: string })?.message
    super(`${label}: ${status}${text ? ` ${text}` : ''}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function detailOf(res: Response): Promise<unknown> {
  const text = await res.text()
  try {
    const parsed = JSON.parse(text)
    return parsed?.detail ?? text
  } catch {
    return text
  }
}

interface Options {
  method?: string
  body?: unknown
  /** Names the operation in error messages, e.g. "dashboard". */
  label: string
}

async function send(path: string, options: Options): Promise<Response> {
  const token = getAccessToken()
  const headers: Record<string, string> = {}
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  return fetch(apiUrl(path), {
    method: options.method ?? 'GET',
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
}

/**
 * Authenticated request. Returns the raw Response so callers that care about a
 * particular status (saveEncounter and its 409) can handle it themselves;
 * everything else goes through json().
 */
export async function request(path: string, options: Options): Promise<Response> {
  let res = await send(path, options)

  if (res.status === 401) {
    // Expired access token: rotate and retry exactly once. A second 401 means
    // the session is genuinely gone.
    const refreshed = await refreshSession()
    if (refreshed) {
      res = await send(path, options)
    }
    if (res.status === 401) {
      clearSession()
      throw new ApiError(options.label, 401, 'Your session has expired. Sign in again.')
    }
  }

  return res
}

async function json<T>(path: string, options: Options): Promise<T> {
  const res = await request(path, options)
  if (!res.ok) throw new ApiError(options.label, res.status, await detailOf(res))
  return res.json() as Promise<T>
}

// --- Auth -------------------------------------------------------------------

export async function login(email: string, password: string): Promise<AuthUser> {
  // Deliberately not via request(): there is no session to refresh yet, and a
  // 401 here means bad credentials, not an expired token.
  const res = await send('/auth/login', {
    method: 'POST',
    body: { email, password },
    label: 'login',
  })
  if (!res.ok) throw new ApiError('login', res.status, await detailOf(res))

  const pair = (await res.json()) as TokenPair
  setSession(pair)
  return pair.user
}

/** Open sign-up. Always creates a patient account and signs them straight in. */
export async function register(
  email: string,
  password: string,
  name: string,
): Promise<AuthUser> {
  const res = await send('/auth/register', {
    method: 'POST',
    body: { email, password, name },
    label: 'register',
  })
  if (!res.ok) throw new ApiError('register', res.status, await detailOf(res))

  const pair = (await res.json()) as TokenPair
  setSession(pair)
  return pair.user
}

export const logout = endSession

export async function fetchMe(): Promise<AuthUser> {
  const data = await json<{ user: AuthUser }>('/auth/me', { label: 'me' })
  return data.user
}

// --- Account administration (admin only) ------------------------------------

export async function fetchAccounts(): Promise<AuthUser[]> {
  const data = await json<{ users: AuthUser[] }>('/auth/users', { label: 'accounts' })
  return data.users
}

export interface NewAccount {
  email: string
  password: string
  role: Role
  name: string
  /** Required for a patient account, rejected for any other role. */
  patient_id?: string | null
}

export async function createAccount(account: NewAccount): Promise<AuthUser> {
  const data = await json<{ user: AuthUser }>('/auth/users', {
    method: 'POST',
    body: account,
    label: 'create account',
  })
  return data.user
}

/** Disabling also revokes the account's live sessions, so access stops at once. */
export async function setAccountActive(
  userId: string,
  active: boolean,
): Promise<AuthUser> {
  const data = await json<{ user: AuthUser }>(`/auth/users/${encodeURIComponent(userId)}`, {
    method: 'PATCH',
    body: { active },
    label: 'update account',
  })
  return data.user
}

/** How a forgotten password is recovered — there is no self-service reset. */
export async function setAccountPassword(
  userId: string,
  password: string,
): Promise<void> {
  await json(`/auth/users/${encodeURIComponent(userId)}/password`, {
    method: 'POST',
    body: { password },
    label: 'set password',
  })
}

// --- Patients ---------------------------------------------------------------

export async function fetchPatients(source: Source): Promise<string[]> {
  const data = await json<{ patient_ids: string[] }>(`/patients?source=${source}`, {
    label: 'patients',
  })
  return data.patient_ids
}

export function fetchDashboard(
  patientId: string,
  source: Source,
): Promise<DashboardBundle> {
  return json<DashboardBundle>(
    `/patients/${encodeURIComponent(patientId)}?source=${source}`,
    { label: 'dashboard' },
  )
}

// --- Clinical validation ----------------------------------------------------

// Resolves to null when the patient has no validation on record yet.
export async function fetchValidation(
  patientId: string,
): Promise<SavedValidation | null> {
  const data = await json<{ validation: SavedValidation | null }>(
    `/patients/${encodeURIComponent(patientId)}/validation`,
    { label: 'validation' },
  )
  return data.validation ?? null
}

// The author is taken from the signed-in account server-side, so it is not sent.
export async function saveValidation(
  patientId: string,
  payload: ValidationPayload,
): Promise<SavedValidation> {
  const data = await json<{ validation: SavedValidation }>(
    `/patients/${encodeURIComponent(patientId)}/validation`,
    { method: 'PUT', body: payload, label: 'validation' },
  )
  return data.validation
}

// --- Clinical review notes --------------------------------------------------

export async function fetchNote(patientId: string): Promise<SavedNote | null> {
  const data = await json<{ note: SavedNote | null }>(
    `/patients/${encodeURIComponent(patientId)}/note`,
    { label: 'note' },
  )
  return data.note ?? null
}

// The author is taken from the signed-in account server-side, so it is not sent.
export async function saveNote(patientId: string, note: string): Promise<SavedNote> {
  const data = await json<{ note: SavedNote }>(
    `/patients/${encodeURIComponent(patientId)}/note`,
    { method: 'PUT', body: { note }, label: 'note' },
  )
  return data.note
}

// --- Monitoring / trends ----------------------------------------------------

// Resolves to null for patients with no saved encounters (all CSV patients).
export async function fetchMonitoring(patientId: string): Promise<MonitoringData | null> {
  const data = await json<{ monitoring: MonitoringData | null }>(
    `/patients/${encodeURIComponent(patientId)}/monitoring`,
    { label: 'monitoring' },
  )
  return data.monitoring ?? null
}

// --- Patient self-service ---------------------------------------------------
//
// These take no patient id: the server resolves the record from the token, which
// is what stops a patient reading or writing anyone else's data.

export function fetchMyDashboard(): Promise<DashboardBundle> {
  return json<DashboardBundle>('/me/dashboard', { label: 'my dashboard' })
}

export async function fetchMyMonitoring(): Promise<MonitoringData | null> {
  const data = await json<{ monitoring: MonitoringData | null }>('/me/monitoring', {
    label: 'my monitoring',
  })
  return data.monitoring ?? null
}

export async function fetchMyNote(): Promise<SavedNote | null> {
  const data = await json<{ note: SavedNote | null }>('/me/note', { label: 'my note' })
  return data.note ?? null
}

/** Null on a first visit, which is the signal to start from schema defaults. */
export async function fetchMyPrefill(): Promise<IntakePrefill | null> {
  const data = await json<{ prefill: IntakePrefill | null }>('/me/intake/prefill', {
    label: 'prefill',
  })
  return data.prefill ?? null
}

/**
 * Record an encounter for the signed-in patient.
 *
 * `visit.patient_id` and `visit.visit_id` are ignored by the server, so repeat
 * submissions append a new visit rather than colliding — no 409 to handle.
 */
export function saveMyEncounter(submission: Submission): Promise<SaveResult> {
  return json<SaveResult>('/me/encounters', {
    method: 'POST',
    body: submission,
    label: 'save',
  })
}

// --- Intake -----------------------------------------------------------------

export function fetchIntakeSchema(): Promise<IntakeSchema> {
  return json<IntakeSchema>('/intake/schema', { label: 'schema' })
}

export async function scoreSubmission(submission: Submission): Promise<Assessment> {
  const data = await json<{ assessment: Assessment }>('/intake/score', {
    method: 'POST',
    body: submission,
    label: 'score',
  })
  return data.assessment
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
  const res = await request('/intake/encounters', {
    method: 'POST',
    body: submission,
    label: 'save',
  })

  if (res.status === 409) {
    const body = await res.json()
    throw new DuplicateVisitConflict(body.detail as DuplicateVisitError)
  }
  if (!res.ok) throw new ApiError('save', res.status, await detailOf(res))
  return res.json()
}
