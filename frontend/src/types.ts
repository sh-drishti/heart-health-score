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
  red_flags: string[]
  score_interval: [number, number] | number[]
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

export interface ValidationPayload {
  patient_id: string
  agreement: 'Yes' | 'No'
  calculated_hhs: number
  doctor_hhs: number
  reason: string
}