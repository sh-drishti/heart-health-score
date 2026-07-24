# Backend — HHS Dashboard API

FastAPI wrapper around the existing Python HHS engine. No scoring logic lives here — it imports and reuses the repo's original modules untouched.

## Files

| File | Purpose |
|---|---|
| `main.py` | FastAPI app: CORS, route definitions, request models. Puts repo root on `sys.path` so shared modules import. |
| `service.py` | Dashboard bundle builder. Loads patient (CSV or MongoDB), runs `calculate_hhs` + `calculate_patient_severity`, sanitizes to JSON-safe output. Also holds the in-memory validation store. |
| `payload_convert.py` | MongoDB encounter payload → patient dict. Own copy of `payload_adapter.py` logic (original has import-time side effects, so it is not imported). Returns plain dicts for clean serialization. |
| `requirements.txt` | `fastapi`, `uvicorn[standard]` — extra deps on top of the repo's root `requirements.txt`. |

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

## Endpoints

| Method | Path | Query | Description |
|---|---|---|---|
| GET | `/api/health` | — | `{"status": "ok"}` |
| GET | `/api/patients` | `source=csv\|payload` | `{"patient_ids": [...]}` |
| GET | `/api/patients/{patient_id}` | `source=csv\|payload` | Dashboard bundle (see below) |
| POST | `/api/validation` | — | Save doctor validation (in-memory, lost on restart) |

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
