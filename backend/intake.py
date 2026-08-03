"""
Intake write path: form submission -> engine -> MongoDB.

Mirrors what hhs_v1_2_ui_app.run_streamlit_app does on every rerun, minus the
Streamlit widgets:

    submitted fields -> FieldRecord dict -> HHSManualScorer.calculate()
                     -> build_encounter_payload -> AssessmentService.save_assessment

Root modules are used as-is. Nothing here re-implements scoring.
"""

from typing import Any, Dict, Optional, Tuple

from hhs_v1_2_ui_app import FieldRecord, HHSManualScorer
from assessment_service import AssessmentService, build_encounter_payload
from backend.intake_schema import all_fields
from backend.service import to_json_safe

FIELD_DEFS = all_fields()


def build_fields(submitted: Dict[str, Dict[str, Any]], lpa_unit: str = "mg/dL") -> Dict[str, FieldRecord]:
    """
    Convert submitted {key: {status, value, months_old}} into FieldRecords.

    Applies the same status/value rules as the Streamlit widgets:
    - a non-"Available" status stores value None and months_old None
    - categorical/yes_no answers of "Unknown" become status Unknown
    - available categorical/yes_no answers carry months_old 0.0
    """

    fields: Dict[str, FieldRecord] = {}

    for key, definition in FIELD_DEFS.items():
        entry = submitted.get(key) or {}
        widget = definition["widget"]
        domain = definition["domain"]
        label = definition["label"]
        unit = lpa_unit if key == "lpa" else definition["unit"]

        if widget in ("select", "yes_no"):
            value = entry.get("value", definition["default"])
            if value is None or str(value) == "Unknown":
                fields[key] = FieldRecord(domain, label, "Unknown", unit, "Unknown", None)
            else:
                fields[key] = FieldRecord(domain, label, value, unit, "Available", 0.0)
            continue

        # number / slider: availability select gates the value
        status = entry.get("status", definition["default_status"])
        if status != "Available":
            fields[key] = FieldRecord(domain, label, None, unit, status, None)
            continue

        value = entry.get("value")
        if value is None:
            value = definition["default"]
        months = entry.get("months_old")
        if months is None:
            months = definition["months_default"]

        fields[key] = FieldRecord(domain, label, float(value), unit, "Available", float(months))

    return fields


def score(submission: Dict[str, Any]) -> Dict[str, Any]:
    """Run the engine over a submission without saving. Used for live preview."""

    visit = submission["visit"]
    lpa_unit = submission.get("lpa_unit", "mg/dL")
    fields = build_fields(submission.get("fields", {}), lpa_unit)

    scorer = HHSManualScorer(
        fields,
        int(visit["age"]),
        str(visit["biological_sex"]),
        str(lpa_unit),
    )
    return to_json_safe(scorer.calculate())


def build_payload(submission: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, FieldRecord]]:
    """Assemble the encounter payload exactly as the Streamlit Save tab does."""

    visit = submission["visit"]
    lpa_unit = submission.get("lpa_unit", "mg/dL")
    fields = build_fields(submission.get("fields", {}), lpa_unit)

    scorer = HHSManualScorer(
        fields,
        int(visit["age"]),
        str(visit["biological_sex"]),
        str(lpa_unit),
    )
    assessment = scorer.calculate()

    payload = build_encounter_payload(
        patient_id=visit["patient_id"],
        visit_id=visit["visit_id"],
        visit_date=visit["visit_date"],
        age=int(visit["age"]),
        biological_sex=visit["biological_sex"],
        region_profile=visit.get("region_profile", ""),
        clinical_setting=visit.get("clinical_setting", ""),
        reviewed_by=visit.get("reviewed_by", ""),
        fields=fields,
        assessment=assessment,
        clinician_note=submission.get("clinician_note", ""),
        lpa_unit=lpa_unit,
    )
    return payload, fields


def find_existing_visit(repo: Any, patient_id: str, visit_id: str) -> Optional[Dict[str, Any]]:
    """
    Existing encounter for this (patient_id, visit_id), if any.

    save_payload always inserts, so without this check a resubmit silently
    creates a duplicate encounter and get_payload returns whichever sorts
    latest by timestamp.
    """

    if not repo.patient_exists(patient_id):
        return None

    for encounter in repo.get_all_encounters(patient_id):
        if encounter.get("visit_id") == visit_id:
            return {
                "visit_id": encounter.get("visit_id"),
                "encounter_timestamp": str(encounter.get("encounter_timestamp")),
            }
    return None


def save(submission: Dict[str, Any], allow_duplicate_visit: bool = False) -> Dict[str, Any]:
    """
    Score and persist an encounter.

    Returns {"status": "saved", ...} on success, or
    {"status": "duplicate_visit", "existing": {...}} when the visit_id is
    already on file and allow_duplicate_visit is False.
    """

    payload, _fields = build_payload(submission)
    visit = payload["visit"]

    service = AssessmentService()

    if not allow_duplicate_visit:
        existing = find_existing_visit(service.repository, visit["patient_id"], visit["visit_id"])
        if existing is not None:
            return {"status": "duplicate_visit", "existing": existing}

    saved = service.save_assessment(payload, patient_profile=submission.get("patient_profile"))

    return {
        "status": "saved",
        "patient_id": saved["patient_id"],
        "visit_id": saved["visit_id"],
        "encounter_id": saved["encounter_id"],
        "timestamp": saved["timestamp"].isoformat(),
        "assessment": to_json_safe(payload["assessment"]),
    }
