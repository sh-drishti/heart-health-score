# Healthy Heart Score Dashboard

Cardiovascular risk dashboard. Two frontends, one engine:

- **New**: React (Vite + Tailwind v4 + shadcn/ui) frontend + FastAPI backend
- **Legacy**: original Streamlit app (untouched, still works)

The Python HHS scoring engine (`hhs_v1_2_ui_app.py`) is shared by both — never modified.

---

## Project Layout

```
heart-health-score/
├── app.py, ui.py, tab2.py, ...   ← legacy Streamlit app (untouched)
├── hhs_v1_2_ui_app.py            ← core scoring engine (shared)
├── adapter.py, severity.py, ...  ← engine helpers (shared)
├── data/                         ← CSV patients, Excel thresholds, sample payload
├── backend/                      ← NEW FastAPI service
│   ├── main.py                   ← app, CORS, endpoints
│   ├── service.py                ← dashboard bundle builder + validation store
│   ├── payload_convert.py        ← payload → patient dict
│   ├── intake_schema.py          ← the 48 intake fields (single source of truth)
│   ├── intake.py                 ← intake write path: score + save
│   ├── notes.py                  ← clinical review notes (MongoDB)
│   └── requirements.txt          ← fastapi, uvicorn
└── frontend/                     ← NEW Vite + React + TS app
    ├── src/pages/                ← LandingPage (/), DashboardPage, IntakePage
    ├── src/components/           ← dashboard components
    ├── src/components/intake/    ← form field renderer + live score preview
    ├── src/components/ui/        ← shadcn/ui primitives
    ├── src/config/domains.ts     ← port of config.py
    ├── src/api/client.ts         ← backend client
    └── src/types.ts              ← API types
```

Both Streamlit apps are ported. `hhs_v1_2_ui_app.py` is two things in one file:
the scoring engine (lines 1–895, shared by everything) and a 490-line Streamlit
data-entry app (`run_streamlit_app`, lines 955–1442). The React `/entry` route
replaces the latter.

## Prerequisites

- Python 3.12+ with the project venv (repo root `venv/`)
- Node.js 18+ (tested on Node 22)
- `.env` in repo root with `MONGODB_URI` + `DATABASE_NAME` (only needed for the `payload` data source; CSV works without it)

## Setup (first time)

```bash
# Python deps (Install root engine + backend dependencies)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # includes backend/requirements.txt via -r

# Frontend deps
cd frontend
npm install
cd ..
```

## Running Backend & Frontend

> **Important**: Do **not** run `uvicorn` inside the `backend/` directory. The backend relies on shared scoring engine modules (`adapter.py`, `severity.py`, `database.py`) and data files (`data/cardio_hhs_2.csv`) located at the repository root. Always run `uvicorn` from the **repository root**.

Two terminals from repo root:

```bash
# Terminal 1 — backend API (run from repo root)
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

```bash
# Terminal 2 — React frontend
cd frontend
npm run dev
```

Open **http://localhost:5173**

Three routes, one bundle:

| Route | View | Audience |
|---|---|---|
| `/` | Workspace chooser | — |
| `/dashboard` | Clinical dashboard (read) | Reviewing clinician |
| `/entry` | Encounter entry (write) | Intake staff |

`/dashboard` and `/entry` carry no navigation to each other — only the chooser
at `/` links to both. They share components, types and the API client, so
role-based access can be layered on per route later without splitting the
project.

The Vite dev server (`vite.config.ts`) automatically proxies all `/api/*` requests to `localhost:8000`, so all FastAPI routes work seamlessly without CORS issues.

## Running with Docker

Two containers: the API, and nginx serving the built frontend and proxying
`/api` to it. Because nginx fronts both, the browser is same-origin and CORS
does not apply to the web app.

```bash
docker compose up -d --build
docker compose logs -f
```

The app is then on <http://localhost:8080>. Set `WEB_PORT` if 8080 is taken
(`WEB_PORT=8090 docker compose up -d`), and `WEB_PORT=80` on a server.

`.env` is read at run time via `env_file` and never baked into an image. The API
will not start without `JWT_SECRET`, by design.

Bootstrap the first admin on a fresh deployment:

```bash
docker compose exec api python seed_users.py --email you@example.com --role admin
```

### What is in the API image

`backend/requirements.txt` only — the Streamlit and analysis stack is excluded,
which is why the image is ~447MB rather than well over a gigabyte. The engine
still scores identically: `hhs_v1_2_ui_app.py` guards its Streamlit import in a
try/except.

Two constraints worth knowing before editing the Dockerfile:

- `WORKDIR` must stay `/app` (the repo root). `severity.py` reads
  `data/feature_mapping_hhs_2.xlsx` at import time via a **relative** path, so
  the process cannot start from anywhere else.
- Root modules are copied by an explicit allowlist, not `COPY . .`. The API
  needs exactly seven: `adapter.py`, `assessment_service.py`, `database.py`,
  `hhs_v1_2_ui_app.py`, `mapping.py`, `notification.py`, `severity.py`. Add to
  that list if a new import appears, or the container will fail at startup.

### Measured resource usage

Single uvicorn worker, against the real Atlas database:

| | idle | 10 concurrent requests |
|---|---|---|
| API container | 100 MB | 104 MB |
| nginx container | 22 MB | 24 MB |
| API CPU | ~0% | 60–83% of one core |

Scoring latency was 0.09s best case, 0.50s median and 1.13s p95 under 10-way
concurrency, with 400/400 requests returning 200. Memory is flat under load, so
**RAM is not the constraint — CPU is.** The API also boots and serves 200/200
requests inside a hard 256MB cap without being OOM-killed, so a 1GB t3.micro has
ample headroom at run time.

Build the frontend image on your machine or in CI rather than on a small
instance: `vite build` under Node needs more memory than a t3.micro comfortably
has.

`--workers` stays at 1 because `service._validations` is still a process-local
dict; a second worker would see a different set of validations.

## Data Sources

Switch in the dashboard header dropdown:

- **CSV (internal)** — reads `data/cardio_hhs_2.csv` (101 synthetic patients)
- **MongoDB payload** — reads encounter payloads via `EncounterRepository` (requires `.env`)

## Authentication

The API requires a bearer token on every route except `GET /api/health`, and the
web app requires a sign-in. Set `JWT_SECRET` in `.env` (see `.env.example`) — the
service refuses to start without it — then create the first admin, since account
administration is the one thing that cannot bootstrap itself:

```bash
python seed_users.py --email you@example.com --role admin --name "Your Name"
python seed_users.py --list
```

Roles:

| Role | Can do | Comes from |
|---|---|---|
| `admin` | Issue accounts, reset passwords, disable access. **No** patient data | `seed_users.py`, then `/admin` in the app |
| `clinician` | Review any patient, notes, validations, intake | An admin |
| `staff` | Intake on someone's behalf | An admin |
| `patient` | Own record only, including recording their own visits | Self-registration at `/register` |

People assessing their own heart health **sign up themselves** at `/register`;
the `patient_id` is issued server-side, never accepted from the request, so no
account can claim someone else's record. Patient reads and writes go through
`/api/v1/me/*`, which resolves the record from the token rather than the URL.

The admin split runs both ways: an account administrator cannot read clinical
data, and a clinician cannot grant access to it.

The same bearer flow serves the web app and a native client, which is why tokens
are used rather than cookies. Refresh tokens rotate on every use.

## API Reference

All routes live under `/api/v1`; `/api/health` is the only exception. Roles in
brackets.

| Endpoint | Description |
|---|---|
| `GET /api/health` | Health check, unauthenticated |
| `POST /api/v1/auth/login` | `{email, password}` → access + refresh token and the user |
| `POST /api/v1/auth/refresh` | `{refresh_token}` → a new pair; the presented one is revoked |
| `POST /api/v1/auth/logout` · `logout-all` | Revoke one session · every session |
| `GET /api/v1/auth/me` | The signed-in account |
| `POST /api/v1/auth/register` | Open sign-up; always a patient, with a server-issued `patient_id` |
| `GET` · `POST /api/v1/auth/users` | List · create accounts *[admin]* |
| `PATCH /api/v1/auth/users/{id}` | Enable or disable an account; disabling revokes its sessions *[admin]* |
| `POST /api/v1/auth/users/{id}/password` | Set a password and end that account's sessions *[admin]* |
| `GET /api/v1/patients?source=csv\|payload` | List patient IDs *[clinician, staff]* |
| `GET /api/v1/patients/{id}?source=csv\|payload` | Full dashboard bundle: `{patient, patient_data, assessment}` *[clinician]* |
| `POST /api/v1/validation` | Save doctor validation `{patient_id, agreement, calculated_hhs, doctor_hhs, reason}` (in-memory) *[clinician]* |
| `GET /api/v1/patients/{id}/note` | Saved clinical review note; `note` is `null` when none exists *[clinician]* |
| `PUT /api/v1/patients/{id}/note` | Save (upsert) the review note `{note}`; the author is the signed-in account *[clinician]* |
| `GET /api/v1/patients/{id}/monitoring` | Trend history; `monitoring` is `null` with no saved encounters *[clinician]* |
| `GET /api/v1/intake/schema` | Intake form definitions: 48 fields with bounds, defaults, units, labels *[clinician, staff]* |
| `POST /api/v1/intake/score` | Score a submission without saving — drives the live preview *[clinician, staff]* |
| `POST /api/v1/intake/encounters` | Score + persist an encounter to MongoDB. `409` if `visit_id` already exists *[clinician, staff]* |
| `GET /api/v1/me/dashboard` · `me/monitoring` · `me/note` | The caller's own record *[patient]* |
| `GET /api/v1/me/intake/prefill` | Last submission, measurement ages advanced, for a repeat visit *[patient]* |
| `POST /api/v1/me/encounters` | Record your own encounter; ids assigned server-side *[patient]* |

Interactive docs: http://localhost:8000/docs (FastAPI Swagger UI)

## Clinical Notes

The notes panel on `/dashboard` persists to MongoDB (`clinical_notes`
collection, one current note per patient) rather than to `localStorage`. A
failed save is reported in the panel instead of silently succeeding locally.

Distinct from the intake `clinician_note`, which belongs to a single encounter
payload. When a patient has no saved review note, the panel falls back to the
intake note as a starting point.

## Data Entry (`/entry`)

The React route at **http://localhost:5173/entry** is a port of the second
Streamlit app — the one embedded in `hhs_v1_2_ui_app.py` as
`run_streamlit_app()`. It writes encounters; `/dashboard` reads them back via
the `payload` source.

```
form (48 fields)  ->  POST /api/intake/score       (live preview, every edit)
                  ->  POST /api/intake/encounters  (score + save)
                        -> assessment_service.build_encounter_payload
                        -> EncounterRepository.save_payload  -> MongoDB
```

Field definitions come from `backend/intake_schema.py` and are served over HTTP
rather than hand-copied into TypeScript. **Changing a bound or default means
editing that one file**, not the React components.

Unlike the Streamlit original, the form shows the assessment as you type. The
original computed it on every rerun but never rendered it.

## Legacy Streamlit Apps

Two separate apps, both still work:

```bash
source venv/bin/activate

streamlit run app.py                # dashboard  -> ported to /dashboard
streamlit run hhs_v1_2_ui_app.py    # data entry -> ported to /entry
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` on backend | Run `pip install -r requirements.txt   # includes backend/requirements.txt via -r` from repo root |
| `FileNotFoundError: data/...` | Ensure you started `uvicorn backend.main:app --reload` from the repo root, NOT inside `backend/` |
| Payload source returns 502 | Check `.env` has valid `MONGODB_URI`; MongoDB reachable |
| Port 5173 busy | Vite auto-picks 5174; backend CORS already allows it |
| Blank severity values | Expected for patients with missing measurements — engine abstains per design |
