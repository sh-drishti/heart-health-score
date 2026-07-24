"""
Payload -> patient conversion for the API backend.

Own copy of payload_adapter.py logic. Existing file not imported because
it has import-time side effects (reads JSON file, prints). This version
returns plain dicts so FastAPI can serialize directly.
"""

from mapping import HHS_FIELD_METADATA

LABEL_TO_KEY = {
    meta["label"]: key
    for key, meta in HHS_FIELD_METADATA.items()
}


def payload_to_patient(payload: dict) -> dict:
    """Convert an HHS encounter payload into dashboard-shaped dicts."""

    patient = {}
    visit = payload["visit"]

    patient["Patient_ID"] = visit["patient_id"]
    patient["patient_id"] = visit["patient_id"]
    patient["age"] = visit["age"]
    patient["biological_sex"] = visit["biological_sex"]

    for feed in payload["input_feeds"]:
        label = feed["label"]
        if label not in LABEL_TO_KEY:
            continue

        key = LABEL_TO_KEY[label]
        patient[key] = feed["value"]

        if feed.get("months_old") is not None:
            patient[f"{key}_months_old"] = feed["months_old"]

        patient[f"{key}_status"] = feed.get("status")

    return {
        "patient": patient,
        "assessment": payload["assessment"],
        "visit": visit,
        "clinician_note": payload.get("clinician_note", ""),
    }
