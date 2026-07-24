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
│   └── requirements.txt          ← fastapi, uvicorn
└── frontend/                     ← NEW Vite + React + TS dashboard
    ├── src/components/           ← dashboard components
    ├── src/components/ui/        ← shadcn/ui primitives
    ├── src/config/domains.ts     ← port of config.py
    ├── src/api/client.ts         ← backend client
    └── src/types.ts              ← API types
```

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

Interactive docs: http://localhost:8000/docs (FastAPI Swagger UI)

## Legacy Streamlit App

```bash
source venv/bin/activate
streamlit run app.py
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` on backend | Run `pip install -r requirements.txt -r backend/requirements.txt` from repo root |
| `FileNotFoundError: data/...` | Ensure you started `uvicorn backend.main:app --reload` from the repo root, NOT inside `backend/` |
| Payload source returns 502 | Check `.env` has valid `MONGODB_URI`; MongoDB reachable |
| Port 5173 busy | Vite auto-picks 5174; backend CORS already allows it |
| Blank severity values | Expected for patients with missing measurements — engine abstains per design |
