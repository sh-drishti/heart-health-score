"""HTTP surface for the additional-parameter collection programme.

Mounted at /api/collect, deliberately outside /api/v1: this is a temporary
programme with its own lifecycle, not part of the versioned clinical API.

Access model. The people filling this in are employees with no accounts, so the
endpoints cannot require a bearer token. Two shared codes gate this instead,
and they are deliberately different secrets:

  COLLECTION_ACCESS_CODE  X-Collection-Code   submit, and read the form schema
  COLLECTION_ADMIN_CODE   X-Admin-Code        read and export everyone's answers

The submission code is circulated to every invited person and travels in their
link, so it must not also unlock the review of everybody's health data. The
admin code is handed out separately and never appears in a URL.

Both are weak authentication and are not pretending otherwise — their job is to
keep unauthenticated endpoints off the open internet, not to establish
identity. If either variable is unset its endpoints refuse to serve rather than
defaulting to open, matching backend/security.py: a silent default is worse
than a visible failure.
"""

import os
import secrets
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from collection import store
from collection.schema import FIELDS_BY_KEY, schema

router = APIRouter(prefix="/api/collect", tags=["parameter collection"])

UNKNOWN = "Unknown"


# ----------------------------------------------------------------------------
# Access
# ----------------------------------------------------------------------------

def _check(supplied: Optional[str], variable: str, what: str) -> None:
    expected = os.getenv(variable, "").strip()

    if not expected:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"{what} is not open. {variable} is not configured.",
        )

    if not supplied or not secrets.compare_digest(supplied.strip(), expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong access code.")


def _require_access(supplied: Optional[str]) -> None:
    """Gate on the code given to the people filling in the form."""

    _check(supplied, "COLLECTION_ACCESS_CODE", "Collection")


def _require_admin(supplied: Optional[str]) -> None:
    """Gate on the separate code for reading everyone's submissions.

    Deliberately a different secret from the submission code: that one is
    circulated to every invited person and travels in a link, so it must not
    also unlock the review of everybody's answers.
    """

    _check(supplied, "COLLECTION_ADMIN_CODE", "Review")


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


# ----------------------------------------------------------------------------
# Review — separate code, reads everyone
# ----------------------------------------------------------------------------

@router.get("/submissions", summary="All submissions (review)")
def list_submissions(x_admin_code: Optional[str] = Header(default=None)):
    """Every submission, newest correction first, with the field definitions
    needed to label the answers."""

    _require_admin(x_admin_code)

    submissions = [
        {
            "employee_code": doc.get("employee_code", ""),
            "full_name": doc.get("full_name", ""),
            "revision": doc.get("revision", 1),
            "created_at": doc["created_at"].isoformat() if doc.get("created_at") else "",
            "updated_at": doc["updated_at"].isoformat() if doc.get("updated_at") else "",
            "answers": doc.get("answers", {}),
        }
        for doc in store.list_submissions()
    ]

    return {"count": len(submissions), "submissions": submissions, **schema()}


@router.get("/submissions.csv", summary="Download submissions as CSV")
def download_csv(x_admin_code: Optional[str] = Header(default=None)):
    """The same columns the desktop tool wrote, so anything already built
    against its CSV keeps working."""

    _require_admin(x_admin_code)

    import csv
    import io

    from collection.export_submissions import COLUMNS, rows

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows())

    return Response(
        # utf-8-sig so Excel opens it without mangling non-ASCII names.
        content=buffer.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="hhs-parameters.csv"'
        },
    )
