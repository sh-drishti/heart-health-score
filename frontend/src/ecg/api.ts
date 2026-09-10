// Client for ECG interpretation.
//
// Goes through the shared authenticated `request` helper — unlike the
// collection form, this lives on /api/v1 and the caller is a signed-in user, so
// bearer-token handling and refresh-on-401 are exactly what we want.

import { request } from '@/api/client'

export interface EcgField {
  key: string
  label: string
  unit: string
  min: number
  max: number
}

export interface EcgTarget {
  key: string
  label: string
  threshold: number
}

export interface EcgSchema {
  model_version: string
  fields: EcgField[]
  targets: EcgTarget[]
}

export interface Prediction {
  label: string
  probability: number
  threshold: number
  positive: boolean
}

export interface Abnormality {
  type: string
  label: string
  probability: number
}

export interface EcgResult {
  model_version: string
  status: 'normal' | 'abnormal'
  input_features: Record<string, number>
  predictions: Record<string, Prediction>
  abnormalities: Abnormality[]
  /** The model is multilabel with independent thresholds, so "Normal" can be
   *  positive at the same time as an abnormality. Shown rather than hidden. */
  norm_and_abnormal: boolean
}

export interface MeasurementError {
  field: string
  message: string
}

export class EcgError extends Error {
  fieldErrors: MeasurementError[]

  constructor(message: string, fieldErrors: MeasurementError[] = []) {
    super(message)
    this.fieldErrors = fieldErrors
  }
}

export async function fetchEcgSchema(): Promise<EcgSchema> {
  const res = await request('/ecg/schema', { label: 'ECG form' })
  if (!res.ok) throw new EcgError('Could not load the form.')
  return res.json()
}

export async function interpret(
  measurements: Record<string, number | null>,
): Promise<EcgResult> {
  const res = await request('/ecg/interpret', {
    method: 'POST',
    body: measurements,
    label: 'ECG interpretation',
  })

  if (res.status === 422) {
    const detail = (await res.json())?.detail
    throw new EcgError(
      detail?.message ?? 'Check these measurements.',
      detail?.errors ?? [],
    )
  }
  if (!res.ok) throw new EcgError('Could not interpret this ECG.')

  return res.json()
}
