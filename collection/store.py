"""MongoDB access for the additional-parameter collection programme.

One collection, `parameter_submissions`, keyed on the employee code so a person
can correct their own entry — the same upsert behaviour the desktop tool had
when it rewrote its CSV row by employee code.

Imports of `database` are lazy, matching backend/notes.py, so an unreachable
MONGODB_URI breaks only the routes that need Mongo rather than app startup.
"""

from datetime import datetime, timezone
from typing import Any, Optional

COLLECTION = "parameter_submissions"


def _collection():
    from database import db

    return db[COLLECTION]


def ensure_indexes() -> None:
    """Employee code is the record's identity, so it must be unique."""

    _collection().create_index("employee_code", unique=True)


def save_submission(
    employee_code: str,
    full_name: str,
    answers: dict[str, Any],
    submitted_from: str = "",
) -> dict:
    """Insert or update one person's submission. Returns what was stored."""

    now = datetime.now(timezone.utc)
    code = employee_code.strip()

    document = {
        "employee_code": code,
        "full_name": full_name.strip(),
        "answers": answers,
        "updated_at": now,
        # Kept for support: "I submitted twice, which one stuck?"
        "submitted_from": submitted_from,
    }

    result = _collection().update_one(
        {"employee_code": code},
        {
            "$set": document,
            "$setOnInsert": {"created_at": now},
            "$inc": {"revision": 1},
        },
        upsert=True,
    )

    return {
        "employee_code": code,
        "created": result.upserted_id is not None,
        "updated_at": now.isoformat(),
    }


def get_submission(employee_code: str) -> Optional[dict]:
    """One submission, for the prefill-on-return case. Not exposed publicly."""

    return _collection().find_one(
        {"employee_code": employee_code.strip()},
        {"_id": 0},
    )


def count_submissions() -> int:
    return _collection().count_documents({})


def list_submissions() -> list[dict]:
    """Every submission, newest correction first. Used by the review page."""

    return list(
        _collection().find({}, {"_id": 0}).sort("updated_at", -1)
    )
