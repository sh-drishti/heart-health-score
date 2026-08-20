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

from backend import (
    auth,
    intake,
    intake_schema,
    monitoring,
    notes,
    self_service,
    service,
    users,
    validations,
)


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


API_DESCRIPTION = """
Cardiovascular risk scoring on the HHS-v1.2 engine, for the clinical web
dashboard and the mobile app.

### Authenticating in this page

1. `POST /api/v1/auth/login` with an account's email and password.
2. Copy `access_token` from the response.
3. Click **Authorize** (top right) and paste it. Every request below then
   carries it, and "Try it out" works for real.

Accounts are not self-serve — a clinician creates them with
`POST /api/v1/auth/users`, and the first one comes from `seed_users.py`.

### Roles

Each endpoint's summary ends with the roles that may call it.

| Role | Can do |
|---|---|
| `admin` | Issue accounts, reset passwords, disable access. **No** patient data |
| `clinician` | Review any patient, write notes and validations, run intake |
| `staff` | Intake on someone's behalf, plus listing patient ids to check for duplicates |
| `patient` | Own record only, through `/me/*` — including recording their own visits |

The admin split runs both ways: an account administrator cannot read clinical
data, and a clinician cannot grant anyone access. Patients self-register at
`POST /auth/register`, so admins only issue the roles that are handed out.

A `patient` token on `/patients/{id}` returns **403** by design: patient clients
resolve their record from the token, never from the URL, so no patient can reach
another patient's data by editing a path.

### Tokens

Access tokens are short-lived (30 min by default). When one expires the API
returns **401**; exchange the refresh token at `POST /api/v1/auth/refresh` for a
new pair. Refresh tokens **rotate** — redeeming one revokes it, so a replay is a
401 and logout genuinely ends the session.
"""

TAGS_METADATA = [
    {"name": "auth", "description": "Sign in, refresh, sign out, and account management."},
    {"name": "patients", "description": "Patient lookup and the full dashboard bundle."},
    {"name": "notes", "description": "Clinical review notes, one current note per patient."},
    {"name": "monitoring", "description": "Longitudinal trends across a patient's encounters."},
    {"name": "intake", "description": "Encounter entry: form schema, live scoring, and saving."},
    {
        "name": "patient self-service",
        "description": (
            "The same data as the clinician routes, from the same service "
            "functions, but scoped to the caller's own record by their token."
        ),
    },
    {"name": "system", "description": "Unauthenticated service probes."},
]

app = FastAPI(
    title="HHS Dashboard API",
    version="1.1.0",
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
    # nginx only proxies /api/, so the default root-level docs paths fall
    # through to the SPA. Serving them under /api keeps one proxy rule.
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

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

# Role shorthands.
#
# A patient is a clinician scoped to one record: same 48-field form, same engine,
# same dashboard — just their own data only. Staff exist to help someone through
# the form, so they share the intake path. Hence AnyUser on the form schema and
# on scoring, both of which read nothing and save nothing.
Clinician = Depends(auth.require_role("clinician"))
ClinicalUser = Depends(auth.require_role("clinician", "staff"))
AnyUser = Depends(auth.require_role("clinician", "staff", "patient"))

# The role a route needs is enforced by a dependency, which OpenAPI cannot see —
# it only records that *some* security applies. Without this the docs would say
# every route is "secured" and leave a reader guessing which token works, so the
# roles go in the summary (visible on the collapsed list) and the 401/403 shapes
# are declared explicitly.
UNAUTHORIZED = {"description": "Missing, malformed, or expired access token."}


def guarded(*roles: str) -> Dict[str, Any]:
    """Route kwargs documenting who may call it. Pair with the matching Depends."""

    return {
        "responses": {
            401: UNAUTHORIZED,
            403: {
                "description": (
                    "Authenticated, but this account's role may not call this "
                    f"endpoint. Requires: {', '.join(roles)}."
                )
            },
        }
    }


def roles_note(*roles: str) -> str:
    return f" [{', '.join(roles)}]"


class ValidationIn(BaseModel):
    """`patient_id` comes from the path and `author` from the token."""

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


@app.get("/api/health", tags=["system"], summary="Liveness probe")
def health():
    """The one route that needs no token, so a load balancer can probe it."""
    return {"status": "ok"}


api = APIRouter(prefix="/api/v1")
api.include_router(auth.router)


# --- Patients (clinician / staff) -------------------------------------------


@api.get(
    "/patients",
    tags=["patients"],
    summary="List patient ids" + roles_note("clinician", "staff"),
    **guarded("clinician", "staff"),
)
def list_patients(source: str = Source, _: Dict[str, Any] = ClinicalUser):
    """
    Ids only. Staff are included so intake can check whether a patient already
    exists before creating a duplicate; opening a record stays clinician-only.
    """
    try:
        ids = service.get_patient_ids(source)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"patient_ids": ids}


@api.get(
    "/patients/{patient_id}",
    tags=["patients"],
    summary="Full dashboard bundle for a patient" + roles_note("clinician"),
    **guarded("clinician"),
)
def patient_dashboard(patient_id: str, source: str = Source, _: Dict[str, Any] = Clinician):
    """`{patient, patient_data, assessment}`, plus `visit` and `clinician_note` for the payload source."""
    try:
        bundle = service.get_dashboard(patient_id, source)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if bundle is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    return bundle


@api.get(
    "/patients/{patient_id}/validation",
    tags=["patients"],
    summary="Read a doctor's agreement with the score" + roles_note("clinician"),
    **guarded("clinician"),
)
def read_validation(patient_id: str, _: Dict[str, Any] = Clinician):
    """Current validation for a patient. `validation` is null when none exists."""
    try:
        saved = validations.get_validation(patient_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"patient_id": patient_id, "validation": saved}


@api.put(
    "/patients/{patient_id}/validation",
    tags=["patients"],
    summary="Record a doctor's agreement with the score" + roles_note("clinician"),
    **guarded("clinician"),
)
def write_validation(
    patient_id: str, body: ValidationIn, user: Dict[str, Any] = Clinician
):
    """
    Upsert: one current validation per patient.

    The author is the signed-in account and is not accepted from the request.
    """
    try:
        saved = validations.save_validation(
            patient_id,
            agreement=body.agreement,
            calculated_hhs=body.calculated_hhs,
            doctor_hhs=body.doctor_hhs,
            reason=body.reason,
            author=auth.actor_name(user),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"patient_id": patient_id, "validation": saved}


# --- Clinical review notes --------------------------------------------------


@api.get(
    "/patients/{patient_id}/note",
    tags=["notes"],
    summary="Read a patient's review note" + roles_note("clinician"),
    **guarded("clinician"),
)
def read_note(patient_id: str, _: Dict[str, Any] = Clinician):
    """Saved review note for a patient. `note` is null when none exists."""
    try:
        saved = notes.get_note(patient_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"patient_id": patient_id, "note": saved}


@api.put(
    "/patients/{patient_id}/note",
    tags=["notes"],
    summary="Save a patient's review note" + roles_note("clinician"),
    **guarded("clinician"),
)
def write_note(patient_id: str, body: NoteIn, user: Dict[str, Any] = Clinician):
    """
    Upsert: one current note per patient.

    The author is the signed-in account and is not accepted from the request —
    sending one has no effect.
    """
    try:
        saved = notes.save_note(patient_id, body.note, auth.actor_name(user))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"status": "ok", "note": saved}


# --- Monitoring / trends ----------------------------------------------------


@api.get(
    "/patients/{patient_id}/monitoring",
    tags=["monitoring"],
    summary="Trend history for a patient" + roles_note("clinician"),
    **guarded("clinician"),
)
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


@api.get(
    "/intake/schema",
    tags=["intake"],
    summary="Intake form field definitions" + roles_note("clinician", "staff", "patient"),
    **guarded("clinician", "staff", "patient"),
)
def intake_form_schema(_: Dict[str, Any] = AnyUser):
    """
    48 fields with bounds, defaults, units and labels, derived from the engine's
    own metadata — so a client never hardcodes the form.
    """
    return intake_schema.schema()


@api.post(
    "/intake/score",
    tags=["intake"],
    summary="Score a submission without saving" + roles_note("clinician", "staff", "patient"),
    **guarded("clinician", "staff", "patient"),
)
def intake_score(submission: SubmissionIn, _: Dict[str, Any] = AnyUser):
    """
    Drives the live preview, so it is called on every edit.

    Open to patients because it reads nothing and saves nothing: the response is
    derived purely from the numbers in the request, so there is no stored record
    to leak whatever `patient_id` the body happens to carry.
    """
    try:
        return {"assessment": intake.score(submission.to_submission())}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@api.post(
    "/intake/encounters",
    tags=["intake"],
    summary="Score and save an encounter" + roles_note("clinician", "staff"),
    responses={
        401: UNAUTHORIZED,
        403: {"description": "Requires: clinician, staff."},
        409: {
            "description": (
                "This visit_id already exists for the patient. The body carries "
                "the existing encounter; resubmit with allow_duplicate_visit "
                "to save anyway."
            )
        },
    },
)
def intake_save(submission: SubmissionIn, user: Dict[str, Any] = ClinicalUser):
    """
    Persists to MongoDB.

    A blank `visit.reviewed_by` is filled in from the signed-in account.
    """

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


@api.get(
    "/me/dashboard",
    tags=["patient self-service"],
    summary="The caller's own dashboard bundle" + roles_note("patient"),
    **guarded("patient"),
)
def my_dashboard(patient_id: str = Depends(auth.current_patient_id)):
    """Same shape as `/patients/{id}`, resolved from the token."""
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


@api.get(
    "/me/monitoring",
    tags=["patient self-service"],
    summary="The caller's own trend history" + roles_note("patient"),
    **guarded("patient"),
)
def my_monitoring(patient_id: str = Depends(auth.current_patient_id)):
    """Same shape as `/patients/{id}/monitoring`, resolved from the token."""
    try:
        data = monitoring.get_monitoring(patient_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"patient_id": patient_id, "monitoring": data}


@api.get(
    "/me/intake/prefill",
    tags=["patient self-service"],
    summary="Last submission, ready to re-edit" + roles_note("patient"),
    **guarded("patient"),
)
def my_prefill(patient_id: str = Depends(auth.current_patient_id)):
    """
    Starting point for a repeat visit, or `prefill: null` on a first visit.

    `fields` is shaped exactly like the POST body. Every `months_old` is advanced
    by the months since that visit, so a reused lab value keeps its real age and
    `data_confidence` decays honestly instead of resetting to fresh.
    """

    try:
        data = self_service.prefill(patient_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"patient_id": patient_id, "prefill": data}


@api.post(
    "/me/encounters",
    tags=["patient self-service"],
    summary="Record your own encounter" + roles_note("patient"),
    **guarded("patient"),
)
def save_my_encounter(
    submission: SubmissionIn,
    user: Dict[str, Any] = Depends(auth.require_role("patient")),
):
    """
    Score and save an encounter for the signed-in patient.

    `visit.patient_id` and `visit.visit_id` in the request are ignored: the id
    comes from the token and the visit id is generated, so a patient can neither
    write to someone else's record nor overwrite one of their own past visits.
    Repeat submissions append, which is what gives the trend charts a second
    point — there is no in-place update.
    """

    patient_id = user.get("patient_id")
    if not patient_id:
        raise HTTPException(
            status_code=403,
            detail="This account is not linked to a patient record",
        )

    try:
        return self_service.save_own_encounter(
            patient_id,
            submission.to_submission(),
            user,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@api.get(
    "/me/note",
    tags=["patient self-service"],
    summary="The caller's own review note" + roles_note("patient"),
    **guarded("patient"),
)
def my_note(patient_id: str = Depends(auth.current_patient_id)):
    """Read-only: a review note is written by a clinician, never by the patient."""
    try:
        saved = notes.get_note(patient_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"patient_id": patient_id, "note": saved}


app.include_router(api)
