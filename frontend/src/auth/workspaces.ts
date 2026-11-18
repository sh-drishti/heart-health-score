import { Activity, ClipboardPlus, HeartPulse, ShieldCheck, Stethoscope } from 'lucide-react'
import type { Role } from '@/types'

/**
 * Every workspace and the roles that can open it. The account decides what a
 * person sees, so there is no chooser: signing in lands on the role's home, and
 * the header lists only the workspaces that role can use.
 *
 * `roles` must match the guards in App.tsx, which mirror the API's own checks.
 */
export interface Workspace {
  to: string
  label: string
  icon: typeof Stethoscope
  roles: Role[]
}

export const WORKSPACES: Workspace[] = [
  { to: '/my-health', label: 'My Heart Health', icon: HeartPulse, roles: ['patient'] },
  { to: '/dashboard', label: 'Dashboard', icon: Stethoscope, roles: ['clinician'] },
  { to: '/admin', label: 'Accounts', icon: ShieldCheck, roles: ['admin'] },
  { to: '/entry', label: 'Encounter Entry', icon: ClipboardPlus, roles: ['clinician', 'staff', 'patient'] },
  { to: '/ecg', label: 'ECG', icon: Activity, roles: ['clinician', 'staff', 'admin'] },
]

/** Where a role lands after signing in, and where `/` sends it. */
export const HOME: Record<Role, string> = {
  admin: '/admin',
  clinician: '/dashboard',
  staff: '/entry',
  patient: '/my-health',
}

export function workspacesFor(role: Role): Workspace[] {
  return WORKSPACES.filter((w) => w.roles.includes(role)).map((w) =>
    // A patient records their own visit; "Encounter Entry" is staff language.
    role === 'patient' && w.to === '/entry' ? { ...w, label: 'Record a Visit' } : w,
  )
}

/**
 * Where to go after signing in. The page that sent someone to sign in wins,
 * but only if their role can open it: otherwise a patient following an old
 * dashboard link would land on "not available to your account".
 */
export function landingFor(role: Role, from?: string | null): string {
  if (from && WORKSPACES.some((w) => w.to === from && w.roles.includes(role))) return from
  return HOME[role]
}
