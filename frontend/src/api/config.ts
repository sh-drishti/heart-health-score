// Where the API lives.
//
// An empty base keeps every request a same-origin relative path, which is what
// the Vite dev proxy forwards to :8000 — so local development needs no .env.
// A deployed build, or a native client pointed at the same API, sets
// VITE_API_BASE to an absolute origin instead.
export const API_BASE = import.meta.env.VITE_API_BASE ?? ''

// Versioned so a client can be pinned to a contract. /api/health is the only
// route outside this prefix.
export const API_PREFIX = '/api/v1'

export const apiUrl = (path: string) => `${API_BASE}${API_PREFIX}${path}`
