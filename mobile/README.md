# Heart Health Score — Expo app

> **On hold since 2026-10-26. Not maintained until further notice.**
>
> The app going to the Play Store is the Flutter app built by the mobile team,
> and the backend is being developed for that client. Nothing here is kept in
> step with the API while it is paused, so expect it to fall behind — check the
> API docs before trusting anything below.

## What exists

Expo SDK 57 · React Native 0.86 · expo-router · TypeScript. Patient-only: it
reads `/api/v1/me/*` and refuses clinician, staff and admin sign-ins.

- **Done:** sign in, refresh token in the device keychain, session restore on
  launch, refresh-on-401, sign out; the Today screen (`/me/dashboard`); a
  design system (`src/constants/theme.ts`).
- **Not started:** Trends (`/me/monitoring`), recording a visit
  (`/intake/schema` + `/me/encounters`), onboarding (`/me/profile`), polish.
- **Template leftovers:** the Explore tab and the
  `com.anonymous.hearthealthscore` Android package id.

`plan.md` records the approach and the decisions behind it, and is the place to
start when this resumes.

## Running it

Self-contained: its own `package.json` and `bun.lock`, nothing shared with the
rest of the repo.

```bash
cd mobile
bun install
cp .env.example .env   # set EXPO_PUBLIC_API_URL — see the comments in it
bunx expo start
```

Expo SDK 57 is newer than most references; `AGENTS.md` points at the versioned
docs, which are the authority.
