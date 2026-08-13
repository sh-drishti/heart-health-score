import { LogOut } from 'lucide-react'
import { useAuth } from '@/auth/AuthContext'
import { Button } from '@/components/ui/button'

const ROLE_LABEL: Record<string, string> = {
  clinician: 'Clinician',
  staff: 'Intake staff',
  patient: 'Patient',
}

/**
 * Signed-in identity and sign-out, for the header.
 *
 * Also the attribution the user should expect to see recorded: review notes are
 * stamped with this account server-side, and the intake form's "Reviewed by" is
 * prefilled from it.
 */
export function UserMenu() {
  const { user, signOut } = useAuth()
  if (user === null) return null

  return (
    <div className="flex items-center gap-2">
      <div className="text-right leading-tight hidden sm:block">
        <div className="text-xs font-medium truncate max-w-40">
          {user.name || user.email}
        </div>
        <div className="text-[11px] text-muted-foreground">
          {ROLE_LABEL[user.role] ?? user.role}
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        onClick={signOut}
        title="Sign out"
        aria-label="Sign out"
      >
        <LogOut className="h-4 w-4" />
      </Button>
    </div>
  )
}
