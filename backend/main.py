"""
FastAPI wrapper around the existing HHS Python engine.

Run from repo root:
    uvicorn backend.main:app --reload --port 8000

Every route lives under /api/v1 and requires a bearer token; /api/health is the
one exception, so a load balancer can probe the service without credentials.
Clinician and staff routes address a patient by id in the path. Patient clients
use /api/v1/me/*, which resolves the record from the token instead — a patient
must not be able to read another patient by editing a URL.
"""

import os
import sys
from pathlib import Path

# Repo root on sys.path so existing modules (adapter, severity, ...) import.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import auth, intake, intake_schema, monitoring, notes, service, users


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Create the auth indexes on boot.

    Tolerates an unreachable database so the service still starts and reports
    the problem per-request, matching how the Mongo-backed modules import lazily.
    """

    try:
        users.ensure_indexes()
    except Exception as exc:  # pragma: no cover - depends on the environment
        print(f"[startup] could not create auth indexes: {exc}", file=sys.stderr)
    yield


app = FastAPI(title="HHS Dashboard API", version="1.1.0", lifespan=lifespan)

# Comma-separated in CORS_ORIGINS so a deployed frontend origin does not need a
# code change. Native clients send no Origin header, so this only affects the
# browser app.
DEFAULT_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174"
)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", DEFAULT_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Source = Query(default="csv", pattern="^(csv|payload)$")

# Role shorthands. Staff run intake; clinicians review, so they can do both.
Clinician = Depends(auth.require_role("clinician"))
ClinicalUser = Depends(auth.require_role("clinician", "staff"))


class ValidationIn(BaseModel):
    patient_id: str
    agreement: str
    calculated_hhs: float
    doctor_hhs: float
    reason: str = ""


class NoteIn(BaseModel):
    """`author` is not accepted from the client — it comes from the token."""

    note: str


class VisitIn(BaseModel):
    patient_id: str
    visit_id: str
    visit_date: str
    age: int = Field(ge=1, le=120)
    biological_sex: str
    region_profile: str = ""
    clinical_setting: str = ""
    reviewed_by: str = ""


class ContactIn(BaseModel):
    email: str = ""
    phone: str = ""


class NotificationPreferencesIn(BaseModel):
    email: bool = True
    push: bool = True


class EmergencyContactIn(BaseModel):
    name: str = ""
    relation: str = ""
    contact: ContactIn = Field(default_factory=ContactIn)


class PatientProfileIn(BaseModel):
    name: str = ""
    contact: ContactIn = Field(default_factory=ContactIn)
    notification_preferences: NotificationPreferencesIn = Field(default_factory=NotificationPreferencesIn)
    emergency_contact: EmergencyContactIn = Field(default_factory=EmergencyContactIn)


class SubmissionIn(BaseModel):
    """One intake form submission. `fields` is {key: {status, value, months_old}}."""

    visit: VisitIn
    patient_profile: PatientProfileIn = Field(default_factory=PatientProfileIn)
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
    """Unauthenticated liveness probe."""
    return {"status": "ok"}


api = APIRouter(prefix="/api/v1")
api.include_router(auth.router)


# --- Patients (clinician / staff) -------------------------------------------


@api.get("/patients")
def list_patients(source: str = Source, _: Dict[str, Any] = ClinicalUser):
    try:
        ids = service.get_patient_ids(source)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"patient_ids": ids}


@api.get("/patients/{patient_id}")
def patient_dashboard(patient_id: str, source: str = Source, _: Dict[str, Any] = Clinician):
    try:
        bundle = service.get_dashboard(patient_id, source)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if bundle is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    return bundle


@api.post("/validation")
def create_validation(validation: ValidationIn, _: Dict[str, Any] = Clinician):
    saved = service.save_validation(validation.model_dump())
    return {"status": "ok", "validation": saved}


# --- Clinical review notes --------------------------------------------------


@api.get("/patients/{patient_id}/note")
def read_note(patient_id: str, _: Dict[str, Any] = Clinician):
    """Saved review note for a patient. `note` is null when none exists."""
    try:
        saved = notes.get_note(patient_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"patient_id": patient_id, "note": saved}


@api.put("/patients/{patient_id}/note")
def write_note(patient_id: str, body: NoteIn, user: Dict[str, Any] = Clinician):
    """Save (upsert) the review note for a patient, attributed to the caller."""
    try:
        saved = notes.save_note(patient_id, body.note, auth.actor_name(user))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"status": "ok", "note": saved}


# --- Monitoring / trends ----------------------------------------------------


@api.get("/patients/{patient_id}/monitoring")
def read_monitoring(patient_id: str, _: Dict[str, Any] = Clinician):
    """
    Trend history across a patient's encounters.

    `monitoring` is null for patients with no saved encounters, which includes
    every CSV-sourced patient.
    """

    try:
        data = monitoring.get_monitoring(patient_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"patient_id": patient_id, "monitoring": data}


# --- Intake (data entry) ----------------------------------------------------


@api.get("/intake/schema")
def intake_form_schema(_: Dict[str, Any] = ClinicalUser):
    """Field definitions for the intake form: bounds, defaults, units, labels."""
    return intake_schema.schema()


@api.post("/intake/score")
def intake_score(submission: SubmissionIn, _: Dict[str, Any] = ClinicalUser):
    """Score a submission without saving. Drives the live preview."""
    try:
        return {"assessment": intake.score(submission.to_submission())}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@api.post("/intake/encounters")
def intake_save(submission: SubmissionIn, user: Dict[str, Any] = ClinicalUser):
    """Score and persist an encounter to MongoDB."""

    payload = submission.to_submission()
    # The signed-in account is the authoritative reviewer; the form field is
    # only a fallback for a name the account does not carry.
    if not payload["visit"].get("reviewed_by"):
        payload["visit"]["reviewed_by"] = auth.actor_name(user)

    try:
        result = intake.save(
            payload,
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


# --- Patient self-service ---------------------------------------------------
#
# Same data as the clinician routes above, from the same service functions, but
# the patient_id comes from the token rather than the path.


@api.get("/me/dashboard")
def my_dashboard(patient_id: str = Depends(auth.current_patient_id)):
    try:
        bundle = service.get_dashboard(patient_id, "payload")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if bundle is None:
        raise HTTPException(
            status_code=404,
            detail="No assessment on file for your record yet",
        )

    return bundle


@api.get("/me/monitoring")
def my_monitoring(patient_id: str = Depends(auth.current_patient_id)):
    try:
        data = monitoring.get_monitoring(patient_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"patient_id": patient_id, "monitoring": data}


@api.get("/me/note")
def my_note(patient_id: str = Depends(auth.current_patient_id)):
    """Read-only: a review note is written by a clinician, never by the patient."""
    try:
        saved = notes.get_note(patient_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"patient_id": patient_id, "note": saved}


app.include_router(api)
