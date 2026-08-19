// TypeScript types mirroring the FastAPI backend JSON shapes.

export type Source = 'csv' | 'payload'

// One parameter's computed info (severity.py output)
export interface ParamInfo {
  value: number | string | null
  severity: number | null
  excel_name: string
  unit: string
}

// Raw patient row (CSV) or converted payload. Loose-typed keyed map.
export type Patient = Record<string, number | string | null>

// Per-feature map keyed by HHS key (e.g. "sbp", "ldl").
export type PatientData = Record<string, ParamInfo>

export interface DomainRow {
  Domain: string
  Weight: number
  Severity: number
  'Main contribution': number
  'Treatment contribution': number
  'Total domain contribution': number
  Status: string
}

export interface Burden {
  total: number
  main: number
  treatment: number
  interaction: number
}

// The engine returns red flags as objects, not strings.
export interface RedFlag {
  flag: string
  message: string
  suppress_score: boolean
}

export interface ScoreInterval {
  floor: number
  expected: number
  optimistic: number
  optimistic_to_expected_width_W: number
  full_width: number
}

export interface Assessment {
  hhs: number
  data_confidence: number
  confidence_label: string
  category: string
  abstained: boolean
  abstention_reasons: string[]
  domain_severities: Record<string, number>
  domain_rows: DomainRow[]
  burden: Burden
  red_flags: RedFlag[]
  score_interval: ScoreInterval
  notes: string[] | string
  metadata?: Record<string, unknown>
}

export interface DashboardBundle {
  patient: Patient
  patient_data: PatientData
  assessment: Assessment
  visit?: Record<string, unknown>
  clinician_note?: string
}

/** What the clinician submits. `patient_id` is in the URL, `author` from the token. */
export interface ValidationPayload {
  agreement: 'Yes' | 'No'
  calculated_hhs: number
  doctor_hhs: number
  reason: string
}

/**
 * A stored validation, as read back from the server.
 *
 * `calculated_hhs` is what the engine said at the time it was recorded, which
 * is not necessarily what it says now — later encounters move the score.
 */
export interface SavedValidation extends ValidationPayload {
  patient_id: string
  author: string
  updated_at: string
}

// A doctor's review note, stored per patient. Distinct from the intake
// clinician_note, which belongs to a single encounter.
export interface SavedNote {
  patient_id: string
  note: string
  author: string
  updated_at: string
}

// --- Monitoring / trends ----------------------------------------------------

export interface HhsTrendPoint {
  date: string
  visit_id: string
  hhs: number
  confidence: number
}

export interface DomainTrendPoint {
  date: string
  burden: number
}

export interface TrendInsights {
  attention_required: string[]
  positive_progress: string[]
}

export interface MonitoringData {
  visit_count: number
  history: {
    hhs_trend: HhsTrendPoint[]
    domain_trends: Record<string, DomainTrendPoint[]>
  }
  current: {
    burden_breakdown: Burden
    red_flags: RedFlag[]
  }
  insights: TrendInsights
}

// --- Auth -------------------------------------------------------------------

/**
 * admin:     accounts only — deliberately no access to clinical data.
 * clinician: review any patient, write notes, run intake.
 * staff:     intake only, on someone else's behalf.
 * patient:   own record only, via /me/* — never by patient_id in a URL.
 */
export type Role = 'admin' | 'clinician' | 'staff' | 'patient'

export interface AuthUser {
  id: string
  email: string
  name: string
  role: Role
  /** Set only for patient accounts; the record /me/* resolves to. */
  patient_id: string | null
  active: boolean
  created_at: string | null
}

/**
 * A returning patient's last submission, ready to re-edit.
 *
 * `months_old` on every numeric field has already been advanced by
 * `months_since_last_visit`, so reused measurements keep their real age and
 * data confidence decays honestly.
 */
export interface IntakePrefill {
  from_visit_id: string
  months_since_last_visit: number
  visit: {
    age: number
    biological_sex: string
    region_profile: string
    clinical_setting: string
  }
  fields: Record<string, FieldEntry>
  lpa_unit: string
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  /** Access-token lifetime in seconds. */
  expires_in: number
  user: AuthUser
}

// --- Intake form ------------------------------------------------------------

export type Availability = 'Available' | 'Unknown' | 'Not measured'

export type FieldWidget =
  | 'number'
  | 'slider'
  | 'select'
  | 'yes_no'
  | 'lpa_unit'
  | 'text'
  | 'date'
  | 'number_plain'
  | 'select_plain'

export interface FieldDef {
  widget: FieldWidget
  key: string
  label: string
  domain?: string
  unit?: string
  min?: number
  max?: number
  default?: number | string | null
  step?: number
  options?: string[]
  default_status?: Availability
  months_default?: number
  months_max?: number
}

export interface FieldGroup {
  title: string
  note: string | null
  fields: FieldDef[]
}

export interface FormSection {
  section: string
  groups: FieldGroup[]
}

export interface FormTab {
  id: string
  title: string
  columns: FormSection[][]
}

export interface IntakeSchema {
  visit_fields: FieldDef[]
  visit_note: string
  tabs: FormTab[]
  availability_options: Availability[]
  yes_no_options: string[]
  clinician_note_default: string
}

// One field's answer. `status` applies to number/slider widgets only.
export interface FieldEntry {
  status?: Availability
  value?: number | string | null
  months_old?: number | null
}

export interface VisitInfo {
  patient_id: string
  visit_id: string
  visit_date: string
  age: number
  biological_sex: string
  region_profile: string
  clinical_setting: string
  reviewed_by: string
}

export interface PatientContact {
  email: string
  phone: string
}

export interface NotificationPreferences {
  email: boolean
  push: boolean
}

export interface EmergencyContact {
  name: string
  relation: string
  contact: PatientContact
}

export interface PatientProfile {
  name: string
  contact: PatientContact
  notification_preferences: NotificationPreferences
  emergency_contact: EmergencyContact
}

export interface Submission {
  visit: VisitInfo
  patient_profile: PatientProfile
  fields: Record<string, FieldEntry>
  clinician_note: string
  lpa_unit: string
  allow_duplicate_visit?: boolean
}

export interface SaveResult {
  status: string
  patient_id: string
  visit_id: string
  encounter_id: string
  timestamp: string
  assessment: Assessment
}

export interface DuplicateVisitError {
  message: string
  existing: { visit_id: string; encounter_timestamp: string }
}
