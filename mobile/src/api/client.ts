/**
 * Authenticated requests.
 *
 * Attaches the bearer token, and on a 401 refreshes once and retries. A second
 * 401 means the session is genuinely gone rather than merely expired, so it
 * clears the session — the auth context is subscribed and the router follows.
 */

import { apiUrl } from './config';
import {
  clearSession,
  getAccessToken,
  refreshSession,
  setSession,
  type AuthUser,
  type TokenPair,
} from './session';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

interface Options {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  /** Used in the error message, so a failure says which call failed. */
  label: string;
}

async function send(path: string, options: Options): Promise<Response> {
  const token = getAccessToken();
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  return fetch(apiUrl(path), {
    method: options.method ?? 'GET',
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
}

/** Returns the raw Response, for callers that care about a particular status. */
export async function request(path: string, options: Options): Promise<Response> {
  let res: Response;

  try {
    res = await send(path, options);
  } catch {
    // fetch only rejects on a transport failure. Worth distinguishing, because
    // "no connection" and "the server said no" need different messages — and
    // on a phone the first is common and not the user's fault.
    throw new ApiError(0, 'Could not reach the server. Check your connection.');
  }

  if (res.status === 401) {
    const refreshed = await refreshSession();
    if (refreshed) res = await send(path, options);

    if (res.status === 401) {
      await clearSession();
      throw new ApiError(401, 'Your session has expired. Sign in again.');
    }
  }

  return res;
}

async function detailOf(res: Response): Promise<string> {
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === 'string') return detail;
    if (detail?.message) return detail.message;
  } catch {
    // Not JSON — a proxy error page, most likely.
  }
  return `Request failed (${res.status})`;
}

export async function json<T>(path: string, options: Options): Promise<T> {
  const res = await request(path, options);
  if (!res.ok) throw new ApiError(res.status, await detailOf(res));
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function signIn(email: string, password: string): Promise<AuthUser> {
  let res: Response;

  try {
    res = await fetch(apiUrl('/auth/login'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim(), password }),
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection.');
  }

  if (!res.ok) {
    // Every login failure is 401 by design — wrong password and unknown email
    // are indistinguishable, so that an address cannot be probed for an
    // account. The message has to be equally vague to preserve that.
    if (res.status === 401) {
      throw new ApiError(401, 'Incorrect email or password.');
    }
    throw new ApiError(res.status, await detailOf(res));
  }

  const pair = (await res.json()) as TokenPair;
  await setSession(pair);
  return pair.user;
}

export async function signOut(): Promise<void> {
  const { getRefreshToken } = await import('./session');
  const token = await getRefreshToken();

  if (token) {
    try {
      await request('/auth/logout', {
        method: 'POST',
        body: { refresh_token: token },
        label: 'sign out',
      });
    } catch {
      // Revoking server-side is best effort. Failing to reach the server must
      // not leave someone stuck signed in on their own device.
    }
  }

  await clearSession();
}

export async function fetchMe(): Promise<AuthUser> {
  // Note the envelope: /auth/me wraps in { user }, while /auth/login returns
  // the user alongside the tokens.
  const body = await json<{ user: AuthUser }>('/auth/me', { label: 'account' });
  return body.user;
}
