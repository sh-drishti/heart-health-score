"""
FastAPI wrapper around the existing HHS Python engine.

Run from repo root:
    uvicorn backend.main:app --reload --port 8000
"""

import sys
from pathlib import Path

# Repo root on sys.path so existing modules (adapter, severity, ...) import.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import intake, intake_schema, notes, service

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


class NoteIn(BaseModel):
    note: str
    author: str = ""


class VisitIn(BaseModel):
    patient_id: str
    visit_id: str
    visit_date: str
    age: int = Field(ge=1, le=120)
    biological_sex: str
    region_profile: str = ""
    clinical_setting: str = ""
    reviewed_by: str = ""


class SubmissionIn(BaseModel):
    """One intake form submission. `fields` is {key: {status, value, months_old}}."""

    visit: VisitIn
    fields: Dict[str, Dict[str, Any]] = {}
    clinician_note: str = ""
    lpa_unit: str = "mg/dL"
    allow_duplicate_visit: bool = False

    def to_submission(self) -> Dict[str, Any]:
        data = self.model_dump()
        data.pop("allow_duplicate_visit", None)
        return data


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


# --- Clinical review notes --------------------------------------------------


@app.get("/api/patients/{patient_id}/note")
def read_note(patient_id: str):
    """Saved review note for a patient. `note` is null when none exists."""
    try:
        saved = notes.get_note(patient_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"patient_id": patient_id, "note": saved}


@app.put("/api/patients/{patient_id}/note")
def write_note(patient_id: str, body: NoteIn):
    """Save (upsert) the review note for a patient."""
    try:
        saved = notes.save_note(patient_id, body.note, body.author)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"status": "ok", "note": saved}


# --- Intake (data entry) ----------------------------------------------------


@app.get("/api/intake/schema")
def intake_form_schema():
    """Field definitions for the intake form: bounds, defaults, units, labels."""
    return intake_schema.schema()


@app.post("/api/intake/score")
def intake_score(submission: SubmissionIn):
    """Score a submission without saving. Drives the live preview."""
    try:
        return {"assessment": intake.score(submission.to_submission())}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/intake/encounters")
def intake_save(submission: SubmissionIn):
    """Score and persist an encounter to MongoDB."""
    try:
        result = intake.save(
            submission.to_submission(),
            allow_duplicate_visit=submission.allow_duplicate_visit,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if result["status"] == "duplicate_visit":
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    f"Visit {submission.visit.visit_id} already exists for patient "
                    f"{submission.visit.patient_id}. Resubmit with allow_duplicate_visit "
                    "to save it anyway."
                ),
                "existing": result["existing"],
            },
        )

    return result
