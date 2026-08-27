// Domain weights, section fields and field labels, mirroring the engine.
// Static constants, no backend dependency.

export interface DomainDef {
  weight: number
  features: string[]
}

export const DOMAINS: Record<string, DomainDef> = {
  'Lipid / Atherogenic Particle': {
    weight: 13,
    features: [
      'total_cholesterol', 'ldl', 'hdl', 'non_hdl', 'triglycerides',
      'tc_hdl_ratio', 'apob', 'lpa',
    ],
  },
  'Blood Pressure / Hemodynamic': {
    weight: 10,
    features: ['sbp', 'dbp', 'lvh', 'resting_hr'],
  },
  Tobacco: {
    weight: 9,
    features: ['smoking_status', 'pack_years', 'years_since_quit', 'smokeless_tobacco'],
  },
  'Glucose / Diabetes': {
    weight: 8,
    features: ['fasting_glucose', 'hba1c', 'diabetes'],
  },
  Adiposity: {
    weight: 8,
    features: ['bmi', 'waist', 'whr'],
  },
  'Inherited Risk': {
    weight: 6,
    features: ['family_history'],
  },
  'Kidney / Vascular Damage': {
    weight: 7,
    features: ['egfr', 'uacr', 'ckd'],
  },
  'Physical Activity': {
    weight: 5,
    features: ['physical_activity'],
  },
  'Diet / Nutrition': {
    weight: 5,
    features: ['diet_score'],
  },
  'Behavioral Risk': {
    weight: 4,
    features: ['alcohol_audit', 'sleep_hours', 'stress_score'],
  },
}

// official domain name used by scorer
export const OFFICIAL_DOMAIN_MAPPING: Record<string, string> = {
  'Lipid / Atherogenic Particle': 'Lipids',
  'Blood Pressure / Hemodynamic': 'Blood Pressure',
  'Glucose / Diabetes': 'Glucose',
  'Kidney / Vascular Damage': 'Kidney',
  Adiposity: 'Adiposity',
  Tobacco: 'Tobacco',
  'Physical Activity': 'Activity',
  'Diet / Nutrition': 'Diet',
  'Behavioral Risk': 'Behavioral',
  'Inherited Risk': 'Inherited Risk',
}

export interface SectionField {
  label: string
  column: string
}

export const SECTION_FIELDS: Record<string, SectionField[]> = {
  'Treatment Status': [
    { label: 'BP Treatment', column: 'bp_treatment' },
    { label: 'Lipid Treatment', column: 'lipid_treatment' },
    { label: 'Glucose Treatment', column: 'glucose_treatment' },
    { label: 'Kidney Treatment', column: 'kidney_treatment' },
    { label: 'Medication Adherence', column: 'adherence_concern' },
  ],
  'Clinical History': [
    { label: 'Known MI', column: 'known_mi' },
    { label: 'Known Stroke', column: 'known_stroke' },
    { label: 'Known Heart Failure', column: 'known_hf' },
    { label: 'Known PAD', column: 'known_pad' },
  ],
  'Safety Alerts': [
    { label: 'Chest Pain', column: 'chest_pain' },
    { label: 'Syncope', column: 'syncope' },
    { label: 'Severe Dyspnea', column: 'severe_dyspnea' },
    { label: 'Neurologic Deficit', column: 'neuro_deficit' },
  ],
  'Optional Advanced Markers': [
    { label: 'CAC', column: 'cac' },
    { label: 'hsCRP', column: 'hscrp' },
    { label: 'Genetic Mutation', column: 'genetic_mutation' },
    { label: 'PRS Percentile', column: 'prs_percentile' },
  ],
}

export const OPTIONAL_MARKER_UNITS: Record<string, string> = {
  CAC: 'Agatston',
  hsCRP: 'mg/L',
  PRS_Percentile: '%',
  Genetic_Mutation: '',
}

// Severity design tokens. Refined clinical palette: emerald / amber / rose.
// Hex values used in charts + inline styles; class tokens used for badges/dots.

export type SeverityLevel = 'ok' | 'warn' | 'risk' | 'neutral'

export const SEVERITY_HEX: Record<SeverityLevel, string> = {
  ok: '#10b981',
  warn: '#f59e0b',
  risk: '#f43f5e',
  neutral: '#94a3b8',
}

export const SEVERITY_UI: Record<
  SeverityLevel,
  { dot: string; badge: string; text: string }
> = {
  ok: {
    dot: 'bg-emerald-500',
    badge: 'bg-emerald-500/15 text-emerald-800 ring-1 ring-inset ring-emerald-600/30 dark:bg-emerald-500/10 dark:text-emerald-400',
    text: 'text-emerald-700 dark:text-emerald-400',
  },
  warn: {
    dot: 'bg-amber-500',
    badge: 'bg-amber-500/15 text-amber-800 ring-1 ring-inset ring-amber-600/30 dark:bg-amber-500/10 dark:text-amber-400',
    text: 'text-amber-700 dark:text-amber-400',
  },
  risk: {
    dot: 'bg-rose-500',
    badge: 'bg-rose-500/15 text-rose-800 ring-1 ring-inset ring-rose-600/30 dark:bg-rose-500/10 dark:text-rose-400',
    text: 'text-rose-700 dark:text-rose-400',
  },
  neutral: {
    dot: 'bg-slate-400',
    badge: 'bg-slate-500/15 text-slate-700 ring-1 ring-inset ring-slate-500/30 dark:bg-slate-500/10 dark:text-slate-400',
    text: 'text-slate-600 dark:text-slate-400',
  },
}

export function getLevel(severity: number | null): SeverityLevel {
  if (severity === null) return 'neutral'
  if (severity < 0.33) return 'ok'
  if (severity < 0.67) return 'warn'
  return 'risk'
}

// severity -> color
export function getColor(severity: number | null): string {
  if (severity === null || severity > 1) return SEVERITY_HEX.neutral
  return SEVERITY_HEX[getLevel(severity)]
}

export function getLabel(severity: number | null): string {
  if (severity === null) return 'N/A'
  if (severity <= 1) {
    if (severity < 0.33) return 'Low'
    if (severity < 0.67) return 'Moderate'
    return 'High'
  }
  return 'N/A'
}

// badge value -> severity level + display text
export function getBadge(value: number | string | null): { level: SeverityLevel | null; display: string } {
  if (value === null || value === undefined || (typeof value === 'number' && Number.isNaN(value))) {
    return { level: null, display: 'Missing' }
  }
  const v = String(value).trim()
  const levels: Record<string, SeverityLevel> = {
    Yes: 'risk',
    No: 'ok',
    Unknown: 'neutral',
    Concern: 'warn',
    Available: 'ok',
    'Not Measured': 'warn',
  }
  if (levels[v]) return { level: levels[v], display: v }
  return { level: null, display: v }
}