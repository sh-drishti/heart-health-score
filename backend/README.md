# Backend — HHS Dashboard API

FastAPI wrapper around the existing Python HHS engine. No scoring logic lives here — it imports and reuses the repo's original modules untouched.

## Files

| File | Purpose |
|---|---|
| `main.py` | FastAPI app: CORS, route definitions, request models, role guards. Puts repo root on `sys.path` so shared modules import. |
| `security.py` | Password hashing and token minting. Pure — no database, no FastAPI. Refuses to import without `JWT_SECRET`. |
| `users.py` | The `users` and `refresh_tokens` collections. The only collections this API owns; the rest keep their existing owners. |
| `auth.py` | `/auth/*` routes plus the dependencies every other route is guarded by (`current_user`, `require_role`, `current_patient_id`). |
| `service.py` | Dashboard bundle builder. Loads patient (CSV or MongoDB), runs `calculate_hhs` + `calculate_patient_severity`, sanitizes to JSON-safe output. |
| `param_severity.py` | Per-parameter severity for the dashboard badges, taken from the engine's own `sev_*` functions. Replaced the root `severity.py`, which banded values from a spreadsheet and misread every risk threshold — see the module docstring. |
| `payload_convert.py` | MongoDB encounter payload → patient dict. Returns plain dicts for clean serialization. |
| `requirements.txt` | The complete dependency set for the API: `fastapi`, `uvicorn[standard]`, `pyjwt`, `bcrypt`, `pandas`, `numpy`, `openpyxl`, `pymongo`, `python-dotenv`. |

## Shared modules reused (read-only, never modified)

- `adapter.calculate_hhs` → official HHS assessment (CSV source)
- `hhs_v1_2_ui_app.sev_*` → per-parameter clinical severities, via `param_severity`
- `database.EncounterRepository` → MongoDB payloads (payload source)
- `mapping` → field metadata (labels, units, domains)

## Run

From **repo root** (not this folder), venv active:

```bash
uvicorn backend.main:app --reload --port 8000
```

> Must run from repo root: `service.py` reads `data/cardio_hhs_2.csv` via relative path, and shared modules read `data/feature_mapping_hhs_2.xlsx`.

Swagger UI: http://localhost:8000/docs

## Authentication

Every route except `GET /api/health` requires `Authorization: Bearer <access_token>`.

Roles: **admin** (accounts only, no clinical data), **clinician** (review any patient, notes, intake), **staff** (intake on someone's behalf), **patient** (`/me/*` only, resolved from the token — never from a `patient_id` in the URL, and including recording their own visits).

The admin split runs both ways: an account administrator cannot read clinical data, and a clinician cannot grant access to it.

Patients self-register at `POST /api/v1/auth/register`. The other roles are issued by an admin, so create the first admin from the repo root — account administration cannot bootstrap itself:

```bash
python seed_users.py --email you@example.com --role admin --name "Your Name"
python seed_users.py --list
```

After that an admin manages accounts at `/admin` in the web app, or via `POST /api/v1/auth/users`. `JWT_SECRET` must be set in `.env` — see `.env.example`; the app refuses to start without it.

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
| POST | `/api/v1/auth/register` | — | Open sign-up; always a patient, `patient_id` issued server-side |
| GET | `/api/v1/auth/users` | admin | List accounts |
| POST | `/api/v1/auth/users` | admin | Create an account; `409` if the email is taken |
| PATCH | `/api/v1/auth/users/{id}` | admin | Enable or disable; disabling revokes its sessions. `409` on the last admin or yourself |
| POST | `/api/v1/auth/users/{id}/password` | admin | Set a password and end that account's sessions |
| GET | `/api/v1/patients` | clinician, staff | `{"patient_ids": [...]}`, `source=csv\|payload` |
| GET | `/api/v1/patients/{patient_id}` | clinician | Dashboard bundle (see below), `source=csv\|payload` |
| POST | `/api/v1/validation` | clinician | Save doctor validation (in-memory, lost on restart) |
| GET | `/api/v1/patients/{id}/note` | clinician | Saved review note; `note` is `null` when none exists |
| PUT | `/api/v1/patients/{id}/note` | clinician | Save the review note `{note}`; the author is the signed-in account |
| GET | `/api/v1/patients/{id}/monitoring` | clinician | Trend history; `monitoring` is `null` with no saved encounters |
| GET | `/api/v1/intake/schema` | clinician, staff, patient | Intake form definitions |
| POST | `/api/v1/intake/score` | clinician, staff, patient | Score without saving — drives the live preview. Reads and writes nothing |
| POST | `/api/v1/intake/encounters` | clinician, staff | Score + persist for a named patient; `409` if `visit_id` exists. Blank `reviewed_by` is filled from the token |
| GET | `/api/v1/me/dashboard` | patient | Own dashboard bundle |
| GET | `/api/v1/me/monitoring` | patient | Own trend history |
| GET | `/api/v1/me/note` | patient | Own review note, read-only |
| GET | `/api/v1/me/intake/prefill` | patient | Last submission with measurement ages advanced, for a repeat visit. `null` on a first visit |
| POST | `/api/v1/me/encounters` | patient | Record own encounter; `patient_id` and `visit_id` in the body are ignored and assigned server-side |

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
