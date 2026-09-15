# Heart Health Score — mobile app

Expo SDK 57 · React Native 0.86 · expo-router · TypeScript

This document is the approach, not a specification. It records decisions and the
reasons behind them, so a later session does not re-litigate them.

---

## What this app is

A patient-facing client for the same FastAPI backend the web dashboard uses. It
is **not** a port of the web app: the web frontend is built for clinicians
reviewing anyone's record, and this one is built for a person reading their own.

Those are different surfaces on purpose. The API already reflects the split —
clinician routes take a `{patient_id}`, and `/me/*` routes resolve the caller's
own record from their token. This app only ever touches `/me/*`, so it is
structurally incapable of reading someone else's data.

## Self-contained, deliberately

No npm workspaces, no shared packages, no scripts reaching outside `mobile/`.
Expo's toolchain is sensitive to changes in the surrounding tree — Metro and
hoisted `node_modules` are a long-standing source of breakage — and the cost of
that coupling is higher than the duplication it would save.

Practically: `mobile/` has its own `package.json`, its own lockfile (`bun.lock`,
while `frontend/` uses npm), and can be deleted or moved to its own repository
without touching anything else.

---

## The three decisions that shape everything

### 1. The API base URL is a real problem, not a config line

The web app gets away with relative paths (`/api/v1/...`) because nginx serves
the frontend and proxies the API from the same origin. There is no nginx in
front of a phone. Every request needs an absolute URL, and that URL differs per
environment in ways that are easy to get wrong:

| running where | base URL |
|---|---|
| Expo Go on a physical phone | the dev machine's LAN IP, e.g. `http://192.168.1.x:8000` — **not** `localhost`, which is the phone |
| Android emulator | `http://10.0.2.2:8000` — the emulator's alias for the host |
| iOS simulator | `http://localhost:8000` works, it shares the host network |
| against the deployed box | the server address |

This goes in `EXPO_PUBLIC_API_URL`, read once in `src/api/config.ts`. Nothing
else in the app should know the base URL.

### 2. Types are generated from the API, never hand-written

The web app keeps a 305-line `types.ts` that mirrors the backend by hand, and
hand-mirrored types drift. The API already publishes a complete OpenAPI
document, so:

```
bunx openapi-typescript $EXPO_PUBLIC_API_URL/api/openapi.json -o src/api/schema.d.ts
```

Committed, regenerated when the API changes. This is also why no shared types
package is needed — both clients generate from the same source independently,
which is better than sharing a file because it cannot go stale silently.

### 3. Tokens live in the keychain, not in storage

The web app keeps its refresh token in `localStorage`, an accepted and
documented XSS tradeoff. A native app has better options and should use them:
`expo-secure-store`, which is Keychain on iOS and Keystore on Android.

The access token stays in memory only. This mirrors the web client's structure
without inheriting its compromise.

Nothing about the backend needs to change for this — auth was built
token-based rather than cookie-based precisely because a native client was
planned.

---

## Structure

```
src/
  app/                  expo-router; the file tree is the navigation
    _layout.tsx         theme + auth gate
    (auth)/sign-in.tsx  signed out
    (tabs)/             signed in
      index.tsx         today: score, trend direction
      trends.tsx        history from /me/monitoring
      record.tsx        /me/intake — record a visit
      profile.tsx       account, sign out
  api/
    config.ts           base URL, the single place it is known
    client.ts           fetch wrapper: bearer header, refresh-on-401
    session.ts          token storage, outside React
    schema.d.ts         generated
  components/           from the template, kept where useful
  constants/theme.ts    template colours; extend, do not replace
```

`session.ts` lives outside React on purpose, the same reasoning as the web
client: `client.ts` needs the token on every request and must refresh on a 401,
and it cannot import a React context to do that.

## The endpoints this app uses

```
POST /api/v1/auth/login          email + password -> access + refresh
POST /api/v1/auth/refresh        rotates; the old refresh token dies
POST /api/v1/auth/logout         revoke this session
GET  /api/v1/auth/me             account

GET  /api/v1/me/dashboard        own score bundle
GET  /api/v1/me/monitoring       own trend history
GET  /api/v1/me/note             own clinical note, read-only
GET  /api/v1/me/intake/prefill   last submission, ready to edit
POST /api/v1/me/encounters       record own visit
GET  /api/v1/intake/schema       the form definition, server-driven
```

`/intake/schema` being server-driven matters: the intake form is data, not code.
Adding a field to the backend changes the form in the app without a release.
Build the renderer against the schema, never hardcode the fields.

---

## Order of work

1. **Auth end to end** — sign in, store the refresh token securely, restore the
   session on launch, refresh on 401, sign out. Nothing else can be tested
   until a request can be authenticated.
2. **Dashboard** — `/me/dashboard`. The first screen that proves the whole
   chain works against real data.
3. **Trends** — `/me/monitoring`.
4. **Record a visit** — `/intake/schema` driven, `POST /me/encounters`.
5. **Polish** — offline states, loading, errors.

Auth first is not arbitrary: every other screen is blocked on it, and it is
where the platform-specific work (secure storage, token lifecycle) lives.

---

## What is deliberately not here

**No clinician features.** No patient lookup, no dashboard for other people, no
notes editing. A patient app that can read someone else's record is a
liability, and the `/me/*` design makes it impossible by construction.

**No hydration or nutrition logging yet.** That is specced separately and needs
decisions that are still open, including a clinical-safety question about the
water goal. It is a later addition, not part of the first version.

**No push notifications.** There is no backend for it —
`send_push_notification` is a stub and no device registration endpoint exists.
Reminders, when they come, are local notifications scheduled on the device.

---

## What blocks a release

This app **cannot ship to either store** against the backend as it stands, for
two independent reasons:

**No HTTPS.** iOS App Transport Security and Android cleartext blocking both
refuse plain HTTP. Development exceptions exist and Apple rejects release
builds that carry them.

**No stable hostname.** The server address is a bare IP with no Elastic IP, and
it has already changed once. A shipped binary carries its API URL; you cannot
chase a moving address through store review.

Neither blocks development. Both block release, and they are now on the
critical path rather than being general good hygiene.

---

## Notes for whoever picks this up

`AGENTS.md` in this directory is worth heeding: Expo SDK 57 is newer than most
training data, and the versioned docs at `docs.expo.dev/versions/v57.0.0/` are
the authority over anything remembered.

The template shipped demo screens (`index.tsx`, `explore.tsx`) and a set of
themed components. The components are worth keeping; the screens are worth
replacing entirely.
