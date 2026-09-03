"""HTTP surface for the additional-parameter collection programme.

Mounted at /api/collect, deliberately outside /api/v1: this is a temporary
programme with its own lifecycle, not part of the versioned clinical API.

Access model. The people filling this in are employees with no accounts, so the
endpoints cannot require a bearer token. Instead a shared access code, supplied
as the X-Collection-Code header, gates both the schema and the write. That is
weak authentication and is not pretending otherwise — its job is to keep an
open write endpoint off the open internet, not to establish identity.

The code is read from COLLECTION_ACCESS_CODE. If that is unset the endpoints
refuse to serve rather than defaulting to open, matching the reasoning in
backend/security.py: a silent default is worse than a visible failure.
"""

import os
import secrets
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from collection import store
from collection.schema import FIELDS_BY_KEY, schema

router = APIRouter(prefix="/api/collect", tags=["parameter collection"])

UNKNOWN = "Unknown"


# ----------------------------------------------------------------------------
# Access
# ----------------------------------------------------------------------------

def _require_access(supplied: Optional[str]) -> None:
    expected = os.getenv("COLLECTION_ACCESS_CODE", "").strip()

    if not expected:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Collection is not open. COLLECTION_ACCESS_CODE is not configured.",
        )

    if not supplied or not secrets.compare_digest(supplied.strip(), expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong access code.")


# ----------------------------------------------------------------------------
# Request model
# ----------------------------------------------------------------------------

class Answer(BaseModel):
    """One field's answer: a value, or an explicit Unknown. Never both, never
    neither — the desktop tool enforced the same rule and it is the reason this
    dataset has no silent blanks."""

    value: Any = None
    unknown: bool = False


class SubmissionIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    employee_code: str = Field(min_length=1, max_length=60)
    answers: dict[str, Answer]
    notes: str = Field(default="", max_length=2000)


# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------

def validate_submission(answers: dict[str, Answer]) -> tuple[dict, list[dict]]:
    """Returns (cleaned answers, errors). Every field must be answered."""

    cleaned: dict[str, Any] = {}
    errors: list[dict] = []

    def fail(key: str, message: str) -> None:
        errors.append({"field": key, "message": message})

    unknown_keys = set(answers) - set(FIELDS_BY_KEY)
    for key in sorted(unknown_keys):
        fail(key, "Not a parameter in this form.")

    for key, field in FIELDS_BY_KEY.items():
        answer = answers.get(key)

        if answer is None:
            fail(key, f"{field['label']} is required — give a value or mark Unknown.")
            continue

        if answer.unknown:
            if answer.value not in (None, ""):
                fail(key, f"{field['label']} is marked Unknown but also has a value.")
                continue
            cleaned[key] = {"value": None, "unknown": True}
            continue

        value = answer.value

        if value is None or (isinstance(value, str) and not value.strip()):
            fail(key, f"{field['label']} is required — give a value or mark Unknown.")
            continue

        if field["kind"] == "number":
            try:
                number = float(value)
            except (TypeError, ValueError):
                fail(key, f"{field['label']} must be a number.")
                continue

            if not (field["min"] <= number <= field["max"]):
                unit = f" {field['unit']}" if field["unit"] else ""
                fail(
                    key,
                    f"{field['label']} must be between {field['min']} and "
                    f"{field['max']}{unit}.",
                )
                continue

            cleaned[key] = {"value": number, "unknown": False}

        elif field["kind"] == "choice":
            text = str(value).strip()
            if text not in field["choices"]:
                fail(key, f"{field['label']}: choose one of {', '.join(field['choices'])}.")
                continue
            # "Unknown" chosen from a dropdown means the same thing as the
            # Unknown checkbox on a numeric field. Store it identically so
            # analysis does not have to know which control produced it.
            cleaned[key] = {
                "value": None if text == UNKNOWN else text,
                "unknown": text == UNKNOWN,
            }

        else:
            cleaned[key] = {"value": str(value).strip(), "unknown": False}

    return cleaned, errors


# ----------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------

@router.get("/schema", summary="Form definition")
def get_schema(x_collection_code: Optional[str] = Header(default=None)):
    """The 25 parameters, grouped into sections in presentation order.

    Gated by the access code so the form can verify it before anyone fills in
    25 fields, rather than rejecting them at submit time.
    """

    _require_access(x_collection_code)
    return schema()


@router.post("/submissions", summary="Submit or correct a record")
def create_submission(
    payload: SubmissionIn,
    request: Request,
    x_collection_code: Optional[str] = Header(default=None),
):
    """Upserts on employee code, so submitting again corrects the earlier entry."""

    _require_access(x_collection_code)

    cleaned, errors = validate_submission(payload.answers)

    if errors:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"message": "Some parameters need attention.", "errors": errors},
        )

    if payload.notes.strip():
        cleaned["_notes"] = {"value": payload.notes.strip(), "unknown": False}

    return store.save_submission(
        employee_code=payload.employee_code,
        full_name=payload.full_name,
        answers=cleaned,
        submitted_from=request.headers.get("x-forwarded-for", "") or "",
    )
