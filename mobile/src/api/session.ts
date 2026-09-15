/**
 * Token storage and the session lifecycle.
 *
 * Deliberately outside React. `client.ts` needs the access token on every
 * request and must be able to refresh on a 401, and it cannot import a React
 * context to do either. The auth context subscribes to this rather than owning
 * it.
 *
 * Where the tokens live:
 *
 *   access token   memory only. It is short-lived (30 minutes) and there is no
 *                  value in persisting something that expires before most
 *                  people reopen the app.
 *   refresh token  expo-secure-store — Keychain on iOS, Keystore on Android.
 *                  This is the credential worth protecting, and it is the one
 *                  place this client improves on the web app, which keeps its
 *                  refresh token in localStorage as a documented XSS tradeoff.
 *
 * SecureStore has no web implementation. This app is primarily native, but the
 * template supports web and `expo start --web` should not throw, so web falls
 * back to localStorage — the same exposure the web dashboard already accepts,
 * and no worse.
 */

import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const REFRESH_KEY = 'hhs.refresh_token';

export type Role = 'admin' | 'clinician' | 'staff' | 'patient';

/**
 * Who this app is for.
 *
 * Every screen reads /me/*, which resolves the caller's own record from their
 * token and returns 403 to anyone else — so a clinician can sign in
 * successfully and then find that nothing loads.
 *
 * This lives here rather than in client.ts because both entry points need it:
 * signing in, and restoring a stored session on launch. A token issued before
 * this rule existed is still in some keychain somewhere.
 */
export const ALLOWED_ROLES: readonly Role[] = ['patient'];

export const isAllowedRole = (role: Role) => ALLOWED_ROLES.includes(role);

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: Role;
  /** Set only for patients. It is what scopes every /me/* route, which is why
   *  this client never sends a patient id anywhere. */
  patient_id: string | null;
  active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

// ---------------------------------------------------------------------------
// Storage
// ---------------------------------------------------------------------------

async function writeRefresh(token: string | null): Promise<void> {
  try {
    if (Platform.OS === 'web') {
      if (token) localStorage.setItem(REFRESH_KEY, token);
      else localStorage.removeItem(REFRESH_KEY);
      return;
    }
    if (token) await SecureStore.setItemAsync(REFRESH_KEY, token);
    else await SecureStore.deleteItemAsync(REFRESH_KEY);
  } catch (error) {
    // A device with no keychain access, or private browsing on web. The
    // session still works for as long as the app stays open; only "still
    // signed in tomorrow" is lost, so this must not be fatal.
    console.warn('[session] could not persist the refresh token', error);
  }
}

async function readRefresh(): Promise<string | null> {
  try {
    if (Platform.OS === 'web') return localStorage.getItem(REFRESH_KEY);
    return await SecureStore.getItemAsync(REFRESH_KEY);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// In-memory state
// ---------------------------------------------------------------------------

let accessToken: string | null = null;
let currentUser: AuthUser | null = null;

type Listener = (user: AuthUser | null) => void;
const listeners = new Set<Listener>();

function notify() {
  for (const listener of listeners) listener(currentUser);
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export const getAccessToken = () => accessToken;
export const getUser = () => currentUser;

export async function setSession(pair: TokenPair): Promise<void> {
  accessToken = pair.access_token;
  currentUser = pair.user;
  await writeRefresh(pair.refresh_token);
  notify();
}

export async function clearSession(): Promise<void> {
  accessToken = null;
  currentUser = null;
  await writeRefresh(null);
  notify();
}

export const getRefreshToken = readRefresh;

// ---------------------------------------------------------------------------
// Refresh
// ---------------------------------------------------------------------------

/**
 * One refresh in flight at a time.
 *
 * Without this, several requests hitting 401 together each start their own
 * refresh. The server rotates the refresh token on every use, so the first to
 * return invalidates the token the others are still holding — and the session
 * dies from what is really a success case. The web client learned this the
 * same way.
 */
let inFlight: Promise<boolean> | null = null;

export function refreshSession(): Promise<boolean> {
  if (!inFlight) {
    inFlight = doRefresh().finally(() => {
      inFlight = null;
    });
  }
  return inFlight;
}

async function doRefresh(): Promise<boolean> {
  const token = await readRefresh();
  if (!token) return false;

  // Imported here rather than at module scope: client.ts imports this module,
  // and a top-level import in both directions is a cycle.
  const { apiUrl } = await import('./config');

  try {
    const res = await fetch(apiUrl('/auth/refresh'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: token }),
    });

    if (!res.ok) {
      await clearSession();
      return false;
    }

    await setSession((await res.json()) as TokenPair);
    return true;
  } catch {
    // A network failure is not an expired session — keep the stored refresh
    // token so the next attempt, on a working connection, can still succeed.
    return false;
  }
}

/** Restore a session on launch. Returns the user, or null if there is none. */
export async function restore(): Promise<AuthUser | null> {
  const token = await readRefresh();
  if (!token) return null;

  await refreshSession();

  // A stored token may predate the role rule, or belong to an account whose
  // role has since changed. Either way it must not open an app it cannot use.
  if (currentUser && !isAllowedRole(currentUser.role)) {
    await clearSession();
    return null;
  }

  return currentUser;
}
