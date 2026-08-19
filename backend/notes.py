"""
Clinical review notes, stored per patient in MongoDB.

Separate from the intake `clinician_note`, which is embedded in an encounter
payload and belongs to the visit. A review note belongs to the patient and is
edited from the dashboard, so it lives in its own collection and works for CSV
patients that have no encounter on file.

Reuses the connection database.py already opens; that module is not modified.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.timeutil import iso_utc

COLLECTION = "clinical_notes"


def _collection():
    # Imported lazily so a missing/unreachable MONGODB_URI only breaks the note
    # endpoints, not the CSV dashboard path.
    from database import db

    return db[COLLECTION]


def get_note(patient_id: str) -> Optional[Dict[str, Any]]:
    """Latest review note for a patient, or None if none has been saved."""

    doc = _collection().find_one({"patient_id": patient_id}, {"_id": 0})
    if doc is None:
        return None

    return {
        "patient_id": doc["patient_id"],
        "note": doc.get("note", ""),
        "author": doc.get("author", ""),
        "updated_at": iso_utc(doc.get("updated_at")),
    }


def save_note(patient_id: str, note: str, author: str = "") -> Dict[str, Any]:
    """Upsert the review note for a patient. One current note per patient."""

    now = datetime.now(timezone.utc)
    _collection().update_one(
        {"patient_id": patient_id},
        {
            "$set": {"note": note, "author": author, "updated_at": now},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    return {
        "patient_id": patient_id,
        "note": note,
        "author": author,
        "updated_at": now.isoformat(),
    }
