import { useCallback, useEffect, useState } from 'react'
import { KeyRound, Loader2, ShieldCheck, UserPlus } from 'lucide-react'
import {
  ApiError,
  createAccount,
  fetchAccounts,
  setAccountActive,
  setAccountPassword,
} from '@/api/client'
import type { AuthUser, Role } from '@/types'
import { useAuth } from '@/auth/AuthContext'
import { AppHeader } from '@/components/AppHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const ROLE_LABEL: Record<Role, string> = {
  admin: 'Admin',
  clinician: 'Clinician',
  staff: 'Intake staff',
  patient: 'Patient',
}

const ROLE_BLURB: Record<Role, string> = {
  admin: 'Manages accounts. No access to patient data.',
  clinician: 'Reviews any patient, writes notes, runs intake.',
  staff: 'Records encounters on someone else’s behalf.',
  patient: 'Their own record only. Normally self-registered.',
}

/**
 * Account administration. Admin only — the API enforces the same, so this page
 * cannot show anything a hand-crafted request could not.
 *
 * Patients normally create their own accounts at /register; this exists for the
 * roles that are issued rather than self-served, and for recovering a password,
 * since there is no self-service reset.
 */
export function AdminPage() {
  const { user } = useAuth()
  const [accounts, setAccounts] = useState<AuthUser[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setErr(null)
    return fetchAccounts()
      .then(setAccounts)
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="min-h-screen bg-background">
      <AppHeader subtitle="Account Administration" />

      <main className="max-w-[1100px] mx-auto px-6 py-6 space-y-6">
        {err && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {err}
          </div>
        )}
        {notice && (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 px-4 py-3 text-sm">
            {notice}
          </div>
        )}

        <CreateAccountForm
          onCreated={(created) => {
            setNotice(`Created ${ROLE_LABEL[created.role].toLowerCase()} account ${created.email}.`)
            load()
          }}
          onError={setErr}
        />

        <section className="space-y-3">
          <div className="flex items-baseline justify-between gap-4">
            <h2 className="text-sm font-semibold">
              Accounts{' '}
              <span className="font-normal text-muted-foreground tabular-nums">
                ({accounts.length})
              </span>
            </h2>
            {loading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          </div>

          <div className="rounded-xl border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="text-left font-semibold px-4 py-2.5">Account</th>
                    <th className="text-left font-semibold px-4 py-2.5">Role</th>
                    <th className="text-left font-semibold px-4 py-2.5">Record</th>
                    <th className="text-left font-semibold px-4 py-2.5">Status</th>
                    <th className="text-right font-semibold px-4 py-2.5">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((account) => (
                    <AccountRow
                      key={account.id}
                      account={account}
                      isSelf={account.id === user?.id}
                      onChanged={(message) => {
                        setNotice(message)
                        load()
                      }}
                      onError={setErr}
                    />
                  ))}
                  {!loading && accounts.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                        No accounts yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <p className="text-xs text-muted-foreground leading-relaxed max-w-2xl">
            Disabling an account revokes its live sessions immediately, so access
            stops without waiting for a token to expire. Accounts are disabled
            rather than deleted, because encounters reference the patient record.
          </p>
        </section>
      </main>
    </div>
  )
}

function CreateAccountForm({
  onCreated,
  onError,
}: {
  onCreated: (created: AuthUser) => void
  onError: (message: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [role, setRole] = useState<Role>('clinician')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [patientId, setPatientId] = useState('')
  const [saving, setSaving] = useState(false)

  const reset = () => {
    setName('')
    setEmail('')
    setPassword('')
    setPatientId('')
    setRole('clinician')
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSaving(true)
    try {
      const created = await createAccount({
        email,
        password,
        role,
        name,
        // Only a patient account may carry one, and it must not be blank.
        patient_id: role === 'patient' ? patientId.trim() : null,
      })
      reset()
      setOpen(false)
      onCreated(created)
    } catch (e) {
      onError(
        e instanceof ApiError && (e.status === 409 || e.status === 422)
          ? String(typeof e.detail === 'string' ? e.detail : e.message)
          : `Could not create the account: ${e instanceof Error ? e.message : String(e)}`,
      )
    } finally {
      setSaving(false)
    }
  }

  if (!open) {
    return (
      <div className="flex items-center justify-between gap-4 rounded-xl border bg-card px-4 py-3">
        <p className="text-sm text-muted-foreground">
          Clinician, staff and admin accounts are issued here. Patients normally
          register themselves.
        </p>
        <Button size="sm" onClick={() => setOpen(true)}>
          <UserPlus className="h-4 w-4" /> New account
        </Button>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="rounded-xl border bg-card p-4 space-y-4">
      <div className="flex items-center gap-2">
        <UserPlus className="h-4 w-4 text-primary" />
        <h2 className="text-sm font-semibold">New account</h2>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="space-y-1.5">
          <Label className="text-xs">Role</Label>
          <Select value={role} onValueChange={(v) => setRole(v as Role)}>
            <SelectTrigger className="h-9">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(['clinician', 'staff', 'admin', 'patient'] as Role[]).map((r) => (
                <SelectItem key={r} value={r}>
                  {ROLE_LABEL[r]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs" htmlFor="new-name">
            Name
          </Label>
          <Input
            id="new-name"
            className="h-9"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs" htmlFor="new-email">
            Email
          </Label>
          <Input
            id="new-email"
            className="h-9"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="off"
            required
          />
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs" htmlFor="new-password">
            Password
          </Label>
          <Input
            id="new-password"
            className="h-9"
            type="text"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            autoComplete="off"
            required
          />
        </div>

        {role === 'patient' && (
          <div className="space-y-1.5 sm:col-span-2">
            <Label className="text-xs" htmlFor="new-pid">
              Existing patient record
            </Label>
            <Input
              id="new-pid"
              className="h-9 font-mono"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              placeholder="HHS-DEMO-0001"
              required
            />
            <p className="text-xs text-muted-foreground">
              Links the account to a record a clinician already created. For a new
              person, let them register themselves instead — the id is issued
              automatically.
            </p>
          </div>
        )}
      </div>

      <p className="text-xs text-muted-foreground">{ROLE_BLURB[role]}</p>

      <div className="flex items-center gap-2">
        <Button type="submit" size="sm" disabled={saving}>
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Creating…
            </>
          ) : (
            'Create account'
          )}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => {
            reset()
            setOpen(false)
          }}
        >
          Cancel
        </Button>
        <span className="text-xs text-muted-foreground">
          The password is shown as you type it — pass it on, there is no reset email.
        </span>
      </div>
    </form>
  )
}

function AccountRow({
  account,
  isSelf,
  onChanged,
  onError,
}: {
  account: AuthUser
  isSelf: boolean
  onChanged: (message: string) => void
  onError: (message: string) => void
}) {
  const [busy, setBusy] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [newPassword, setNewPassword] = useState('')

  const fail = (e: unknown, fallback: string) =>
    onError(
      e instanceof ApiError && (e.status === 409 || e.status === 422)
        ? String(typeof e.detail === 'string' ? e.detail : e.message)
        : `${fallback}: ${e instanceof Error ? e.message : String(e)}`,
    )

  const toggle = async () => {
    setBusy(true)
    try {
      await setAccountActive(account.id, !account.active)
      onChanged(
        account.active
          ? `Disabled ${account.email} and ended its sessions.`
          : `Re-enabled ${account.email}.`,
      )
    } catch (e) {
      fail(e, 'Could not update the account')
    } finally {
      setBusy(false)
    }
  }

  const savePassword = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    try {
      await setAccountPassword(account.id, newPassword)
      onChanged(`Set a new password for ${account.email}. Its sessions were ended.`)
      setNewPassword('')
      setResetting(false)
    } catch (e) {
      fail(e, 'Could not set the password')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <tr className="border-b last:border-b-0">
        <td className="px-4 py-3">
          <div className="font-medium">
            {account.name || '—'}
            {isSelf && <span className="text-muted-foreground font-normal"> (you)</span>}
          </div>
          <div className="text-xs text-muted-foreground">{account.email}</div>
        </td>
        <td className="px-4 py-3">
          <span className="inline-flex items-center gap-1.5">
            {account.role === 'admin' && <ShieldCheck className="h-3.5 w-3.5 text-primary" />}
            {ROLE_LABEL[account.role]}
          </span>
        </td>
        <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
          {account.patient_id ?? '—'}
        </td>
        <td className="px-4 py-3">
          {account.active ? (
            <Badge variant="outline">Active</Badge>
          ) : (
            <Badge variant="destructive">Disabled</Badge>
          )}
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center justify-end gap-1.5">
            <Button
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={() => setResetting((v) => !v)}
              title="Set a new password"
            >
              <KeyRound className="h-3.5 w-3.5" />
              Password
            </Button>
            <Button
              size="sm"
              variant={account.active ? 'outline' : 'default'}
              disabled={busy || isSelf}
              onClick={toggle}
              // The API refuses this anyway; disabling the control explains why
              // before someone clicks it.
              title={isSelf ? 'You cannot disable your own account' : undefined}
            >
              {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {account.active ? 'Disable' : 'Enable'}
            </Button>
          </div>
        </td>
      </tr>

      {resetting && (
        <tr className="border-b last:border-b-0 bg-muted/30">
          <td colSpan={5} className="px-4 py-3">
            <form onSubmit={savePassword} className="flex flex-wrap items-end gap-2">
              <div className="space-y-1.5">
                <Label className="text-xs" htmlFor={`pw-${account.id}`}>
                  New password for {account.email}
                </Label>
                <Input
                  id={`pw-${account.id}`}
                  className="h-9 w-64"
                  type="text"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  minLength={8}
                  autoComplete="off"
                  required
                  autoFocus
                />
              </div>
              <Button type="submit" size="sm" disabled={busy}>
                Set password
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => {
                  setNewPassword('')
                  setResetting(false)
                }}
              >
                Cancel
              </Button>
              <span className="text-xs text-muted-foreground pb-2">
                Ends every session this account has.
              </span>
            </form>
          </td>
        </tr>
      )}
    </>
  )
}
