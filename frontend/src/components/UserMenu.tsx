import { LogOut } from 'lucide-react'
import { useAuth } from '@/auth/AuthContext'
import { Button } from '@/components/ui/button'

/**
 * Sign-out, for the header.
 *
 * The signed-in name and role used to show here too. The header redesign
 * dropped them for now; where (or whether) identity should appear is still
 * open.
 */
export function UserMenu() {
  const { user, signOut } = useAuth()
  if (user === null) return null

  return (
    <Button variant="ghost" size="icon" onClick={signOut} title="Sign out" aria-label="Sign out">
      <LogOut className="h-4 w-4" />
    </Button>
  )
}
