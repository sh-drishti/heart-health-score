/**
 * Where the API lives.
 *
 * The web dashboard gets away with relative paths because nginx serves it and
 * proxies /api from the same origin. A phone has no nginx, so every request
 * needs an absolute URL — and the correct one differs by where the app is
 * running, which is the part that catches people out:
 *
 *   physical device (Expo Go)  the dev machine's LAN address, e.g.
 *                              http://192.168.1.20:8000 — NOT localhost,
 *                              which on a phone is the phone
 *   Android emulator           http://10.0.2.2:8000 (its alias for the host)
 *   iOS simulator              http://localhost:8000 (shares the host network)
 *   deployed                   the server's address
 *
 * Set EXPO_PUBLIC_API_URL in .env. The EXPO_PUBLIC_ prefix is what makes it
 * readable at runtime; anything else is stripped from the bundle.
 *
 * This is the only module that knows the base URL.
 */

const configured = process.env.EXPO_PUBLIC_API_URL?.trim();

if (!configured) {
  // Loud rather than a silent fallback to localhost, which on a physical
  // device fails with a confusing network error rather than a clear cause.
  console.warn(
    '[api] EXPO_PUBLIC_API_URL is not set. Copy .env.example to .env and ' +
      'point it at the backend. On a physical device this must be your ' +
      "machine's LAN address, not localhost.",
  );
}

export const API_BASE = (configured ?? '').replace(/\/+$/, '');

/** Versioned so a client can be pinned to a contract. */
export const API_PREFIX = '/api/v1';

export const apiUrl = (path: string) => `${API_BASE}${API_PREFIX}${path}`;
