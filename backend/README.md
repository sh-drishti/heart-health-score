# Backend — HHS Dashboard API

FastAPI wrapper around the existing Python HHS engine. No scoring logic lives here — it imports and reuses the repo's original modules untouched.

## Files

| File | Purpose |
|---|---|
| `main.py` | FastAPI app: CORS, route definitions, request models, role guards. Puts repo root on `sys.path` so shared modules import. |
| `security.py` | Password hashing and token minting. Pure — no database, no FastAPI. Refuses to import without `JWT_SECRET`. |
| `users.py` | The `users` and `refresh_tokens` collections. The only collections this API owns; the rest keep their existing owners. |
| `auth.py` | `/auth/*` routes plus the dependencies every other route is guarded by (`current_user`, `require_role`, `current_patient_id`). |
| `service.py` | Dashboard bundle builder. Loads patient (CSV or MongoDB), runs `calculate_hhs` + `calculate_patient_severity`, sanitizes to JSON-safe output. Also holds the in-memory validation store. |
| `payload_convert.py` | MongoDB encounter payload → patient dict. Own copy of `payload_adapter.py` logic (original has import-time side effects, so it is not imported). Returns plain dicts for clean serialization. |
| `requirements.txt` | `fastapi`, `uvicorn[standard]`, `pyjwt`, `bcrypt` — extra deps on top of the repo's root `requirements.txt`. |

## Shared modules reused (read-only, never modified)

- `adapter.calculate_hhs` → official HHS assessment (CSV source)
- `severity.calculate_patient_severity` → per-parameter severities (both sources)
- `database.EncounterRepository` → MongoDB payloads (payload source)
- `mapping`, `config` → field metadata, domains

## Run

From **repo root** (not this folder), venv active:

```bash
uvicorn backend.main:app --reload --port 8000
```

> Must run from repo root: `service.py` reads `data/cardio_hhs_2.csv` via relative path, and shared modules read `data/feature_mapping_hhs_2.xlsx`.

Swagger UI: http://localhost:8000/docs

## Authentication

Every route except `GET /api/health` requires `Authorization: Bearer <access_token>`.

Roles: **clinician** (review any patient, notes, intake, manage accounts), **staff** (intake only), **patient** (`/me/*` only, resolved from the token — never from a `patient_id` in the URL).

Accounts are not self-serve. Create the first clinician from the repo root:

```bash
python seed_users.py --email you@example.com --role clinician --name "Dr Rao"
python seed_users.py --list
```

After that a clinician can create accounts with `POST /api/v1/auth/users`. `JWT_SECRET` must be set in `.env` — see `.env.example`; the app refuses to start without it.

Access tokens are short-lived (`ACCESS_TOKEN_TTL_MIN`, default 30). Refresh tokens are opaque, stored only as a SHA-256 hash, and **rotate on every use** — redeeming one revokes it, so a replay returns 401.

## Endpoints

All routes are under `/api/v1`. `/api/health` is the only exception.

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/api/health` | — | `{"status": "ok"}`, unauthenticated |
| POST | `/api/v1/auth/login` | — | `{email, password}` → access + refresh token and the user |
| POST | `/api/v1/auth/refresh` | — | `{refresh_token}` → a new pair; the presented token is revoked |
| POST | `/api/v1/auth/logout` | — | Revoke one session |
| POST | `/api/v1/auth/logout-all` | any | Revoke every session for the caller |
| GET | `/api/v1/auth/me` | any | The signed-in account |
| GET | `/api/v1/auth/users` | clinician | List accounts |
| POST | `/api/v1/auth/users` | clinician | Create an account; `409` if the email is taken |
| GET | `/api/v1/patients` | clinician, staff | `{"patient_ids": [...]}`, `source=csv\|payload` |
| GET | `/api/v1/patients/{patient_id}` | clinician | Dashboard bundle (see below), `source=csv\|payload` |
| POST | `/api/v1/validation` | clinician | Save doctor validation (in-memory, lost on restart) |
| GET | `/api/v1/patients/{id}/note` | clinician | Saved review note; `note` is `null` when none exists |
| PUT | `/api/v1/patients/{id}/note` | clinician | Save the review note `{note}`; the author is the signed-in account |
| GET | `/api/v1/patients/{id}/monitoring` | clinician | Trend history; `monitoring` is `null` with no saved encounters |
| GET | `/api/v1/intake/schema` | clinician, staff | Intake form definitions |
| POST | `/api/v1/intake/score` | clinician, staff | Score without saving — drives the live preview |
| POST | `/api/v1/intake/encounters` | clinician, staff | Score + persist; `409` if `visit_id` exists. Blank `reviewed_by` is filled from the token |
| GET | `/api/v1/me/dashboard` | patient | Own dashboard bundle |
| GET | `/api/v1/me/monitoring` | patient | Own trend history |
| GET | `/api/v1/me/note` | patient | Own review note, read-only |

### Dashboard bundle response

```json
{
  "patient": { "Patient_ID": "...", "age": 54, "sbp": 146, ... },
  "patient_data": {
    "sbp": { "value": 146, "severity": 1, "excel_name": "Systolic BP", "unit": "mmHg" }
  },
  "assessment": {
    "hhs": 64.5,
    "data_confidence": 93.8,
    "confidence_label": "High",
    "domain_severities": { "Lipids": 0.78, ... },
    "domain_rows": [ ... ],
    "burden": { "total": 35.54, "main": 35.54, "treatment": 0.0, "interaction": 0.0 },
    "red_flags": [ ... ]
  }
}
```

Payload source adds `visit` + `clinician_note`. Assessment comes from the payload itself (pre-computed upstream), not re-scored.

### Validation body

```json
{
  "patient_id": "SYN-0001",
  "agreement": "No",
  "calculated_hhs": 64.5,
  "doctor_hhs": 70.0,
  "reason": "optional"
}
```

## Error behavior

| Code | When |
|---|---|
| 404 | Patient ID not found in the selected source |
| 502 | Backend data source failed (MongoDB unreachable, CSV unreadable, scorer error) — `detail` carries the original exception message |

## Environment

- `.env` at **repo root** with `MONGODB_URI` + `DATABASE_NAME` — required only for `source=payload`. `database.py` loads it via `python-dotenv`.
- CORS allows `localhost:5173` + `localhost:5174` (Vite dev). Vite proxies `/api` so CORS is only relevant for direct browser calls.
