"""
FastAPI wrapper around the existing HHS Python engine.

Run from repo root:
    uvicorn backend.main:app --reload --port 8000
"""

import sys
from pathlib import Path

# Repo root on sys.path so existing modules (adapter, severity, ...) import.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend import service

app = FastAPI(title="HHS Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Source = Query(default="csv", pattern="^(csv|payload)$")


class ValidationIn(BaseModel):
    patient_id: str
    agreement: str
    calculated_hhs: float
    doctor_hhs: float
    reason: str = ""


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/patients")
def list_patients(source: str = Source):
    try:
        ids = service.get_patient_ids(source)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"patient_ids": ids}


@app.get("/api/patients/{patient_id}")
def patient_dashboard(patient_id: str, source: str = Source):
    try:
        bundle = service.get_dashboard(patient_id, source)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if bundle is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    return bundle


@app.post("/api/validation")
def create_validation(validation: ValidationIn):
    saved = service.save_validation(validation.model_dump())
    return {"status": "ok", "validation": saved}
