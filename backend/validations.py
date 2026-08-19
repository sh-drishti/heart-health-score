"""
A clinician's agreement (or disagreement) with a calculated score, stored per
patient in MongoDB.

This was an in-process dict in service.py. That lost every validation on
restart, and nothing could read one back even while the service ran — the
getter existed but no route called it. So a cardiologist could record "the
engine says 61.6, I say 48, because the LDL is stale", see a success message,
and have that judgment be unrecoverable. It is the data the engine would be
recalibrated against, which makes it the worst thing in the app to discard.

One current validation per patient, replaced on save, matching the dict
semantics it grew out of. Sits alongside clinical_notes and reuses the
connection database.py already opens; that module is not modified.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.timeutil import iso_utc

COLLECTION = "clinical_validations"


def _collection():
    # Imported lazily so a missing/unreachable MONGODB_URI only breaks the
    # validation endpoints, not the CSV dashboard path.
    from database import db

    return db[COLLECTION]


def get_validation(patient_id: str) -> Optional[Dict[str, Any]]:
    """Current validation for a patient, or None if none has been recorded."""

    doc = _collection().find_one({"patient_id": patient_id}, {"_id": 0})
    if doc is None:
        return None

    return {
        "patient_id": doc["patient_id"],
        "agreement": doc.get("agreement", ""),
        "calculated_hhs": doc.get("calculated_hhs"),
        "doctor_hhs": doc.get("doctor_hhs"),
        "reason": doc.get("reason", ""),
        "author": doc.get("author", ""),
        "updated_at": iso_utc(doc.get("updated_at")),
    }


def save_validation(
    patient_id: str,
    agreement: str,
    calculated_hhs: float,
    doctor_hhs: float,
    reason: str = "",
    author: str = "",
) -> Dict[str, Any]:
    """
    Upsert the validation for a patient.

    `calculated_hhs` is stored as well as the doctor's figure: the point of the
    record is the delta between them, and the engine's output for this patient
    changes as new encounters arrive, so it cannot be recovered later.
    """

    now = datetime.now(timezone.utc)
    _collection().update_one(
        {"patient_id": patient_id},
        {
            "$set": {
                "agreement": agreement,
                "calculated_hhs": calculated_hhs,
                "doctor_hhs": doctor_hhs,
                "reason": reason,
                "author": author,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    return {
        "patient_id": patient_id,
        "agreement": agreement,
        "calculated_hhs": calculated_hhs,
        "doctor_hhs": doctor_hhs,
        "reason": reason,
        "author": author,
        "updated_at": now.isoformat(),
    }
