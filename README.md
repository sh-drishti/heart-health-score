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
pip install -r requirements.txt -r backend/requirements.txt

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

## Data Sources

Switch in the dashboard header dropdown:

- **CSV (internal)** — reads `data/cardio_hhs_2.csv` (101 synthetic patients)
- **MongoDB payload** — reads encounter payloads via `EncounterRepository` (requires `.env`)

## API Reference

| Endpoint | Description |
|---|---|
| `GET /api/health` | Health check |
| `GET /api/patients?source=csv\|payload` | List patient IDs |
| `GET /api/patients/{id}?source=csv\|payload` | Full dashboard bundle: `{patient, patient_data, assessment}` |
| `POST /api/validation` | Save doctor validation `{patient_id, agreement, calculated_hhs, doctor_hhs, reason}` (in-memory) |
| `GET /api/patients/{id}/note` | Saved clinical review note; `note` is `null` when none exists |
| `PUT /api/patients/{id}/note` | Save (upsert) the review note `{note, author}` → MongoDB |
| `GET /api/intake/schema` | Intake form definitions: 48 fields with bounds, defaults, units, labels |
| `POST /api/intake/score` | Score a submission without saving — drives the live preview |
| `POST /api/intake/encounters` | Score + persist an encounter to MongoDB. `409` if `visit_id` already exists |

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
| `ModuleNotFoundError` on backend | Run `pip install -r requirements.txt -r backend/requirements.txt` from repo root |
| `FileNotFoundError: data/...` | Ensure you started `uvicorn backend.main:app --reload` from the repo root, NOT inside `backend/` |
| Payload source returns 502 | Check `.env` has valid `MONGODB_URI`; MongoDB reachable |
| Port 5173 busy | Vite auto-picks 5174; backend CORS already allows it |
| Blank severity values | Expected for patients with missing measurements — engine abstains per design |
