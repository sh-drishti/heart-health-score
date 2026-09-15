/**
 * Session state for React.
 *
 * This does not own the tokens — `api/session.ts` does, because `api/client.ts`
 * needs them outside React. This subscribes to that store and re-renders, which
 * means a session cleared deep inside a failed request still moves the router.
 */

import { createContext, use, useEffect, useState, type PropsWithChildren } from 'react';

import * as client from '@/api/client';
import { restore, subscribe, type AuthUser } from '@/api/session';

interface SessionValue {
  user: AuthUser | null;
  /** True until the stored refresh token has been checked on launch. */
  loading: boolean;
  signIn: (email: string, password: string) => Promise<AuthUser>;
  signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionValue | null>(null);

export function useSession(): SessionValue {
  const value = use(SessionContext);
  if (!value) {
    throw new Error('useSession must be used inside <SessionProvider>');
  }
  return value;
}

export function SessionProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Subscribe before restoring, so a session cleared during the restore is
    // not missed.
    const unsubscribe = subscribe(setUser);

    let cancelled = false;
    restore()
      .then((restored) => {
        if (!cancelled) setUser(restored);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, []);

  return (
    <SessionContext
      value={{
        user,
        loading,
        signIn: client.signIn,
        signOut: client.signOut,
      }}>
      {children}
    </SessionContext>
  );
}
