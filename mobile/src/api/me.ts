/**
 * The patient's own record.
 *
 * Every route here is /me/*, which resolves the caller from their token. This
 * client never sends a patient id anywhere — it does not have one to send, and
 * that is the point: there is no request it could make for someone else's data.
 *
 * Types are hand-written for now rather than generated from the OpenAPI
 * document, because only a small part of a large response is used. See plan.md
 * — generating becomes worth it once more of the payload is consumed.
 */

import { json } from './client';

/** How much a domain adds to the burden, and how bad it looks. */
export interface DomainRow {
  Domain: string;
  Weight: number;
  /** 0–1. Shown as the Status word rather than the number: a patient reading
   *  "0.429" learns nothing. */
  Severity: number;
  'Main contribution': number;
  'Treatment contribution': number;
  'Total domain contribution': number;
  Status: 'Low' | 'Mild' | 'Moderate' | 'High' | string;
}

export interface RecommendedInput {
  Field: string;
  Domain: string;
  'Expected impact points': number;
  Priority: string;
}

export interface Assessment {
  /** 0–100, and higher is better: it is 100 minus the total burden. */
  hhs: number;
  category: string;
  /** How complete the inputs were, not how certain the health picture is. */
  data_confidence: number;
  confidence_label: string;
  score_interval: {
    floor: number;
    expected: number;
    optimistic: number;
  };
  burden: {
    total: number;
    main: number;
    treatment: number;
    interaction: number;
  };
  domain_rows: DomainRow[];
  red_flags: unknown[];
  recommended_inputs?: RecommendedInput[];
  notes?: string[];
}

export interface Visit {
  visit_id: string;
  visit_date: string;
  clinical_setting: string;
  reviewed_by: string;
}

export interface Dashboard {
  /** 127 fields of raw parameters. Not read here — the domain rows are the
   *  patient-facing summary of the same thing. */
  patient: Record<string, unknown>;
  patient_data: Record<string, unknown>;
  assessment: Assessment;
  visit: Visit;
  clinician_note: string;
}

export const fetchDashboard = () =>
  json<Dashboard>('/me/dashboard', { label: 'your score' });

export interface TrendPoint {
  date: string;
  visit_id: string;
  hhs: number;
  confidence: number;
}

export interface Monitoring {
  patient_id: string;
  monitoring: {
    visit_count: number;
    history: { hhs_trend: TrendPoint[] };
  };
}

export const fetchMonitoring = () =>
  json<Monitoring>('/me/monitoring', { label: 'your history' });
