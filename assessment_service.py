from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict


def build_encounter_payload(
    *,
    patient_id: str,
    visit_id: str,
    visit_date: Any,
    age: int,
    biological_sex: str,
    region_profile: str,
    clinical_setting: str,
    reviewed_by: str,
    fields: Dict[str, Any],
    assessment: Dict[str, Any],
    clinician_note: str,
    lpa_unit: str,
) -> Dict[str, Any]:
    return {
        "visit": {
            "patient_id": patient_id,
            "visit_id": visit_id,
            "visit_date": str(visit_date),
            "age": int(age),
            "biological_sex": biological_sex,
            "region_profile": region_profile,
            "clinical_setting": clinical_setting,
            "reviewed_by": reviewed_by,
        },
        "input_feeds": [asdict(rec) for rec in fields.values()],
        "assessment": assessment,
        "clinician_note": clinician_note,
        "lpa_unit": lpa_unit,
    }


class AssessmentService:
    def __init__(self, repository: Any | None = None):
        if repository is None:
            from database import EncounterRepository

            repository = EncounterRepository()
        self.repository = repository

    def save_assessment(self, payload: Dict[str, Any], patient_profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
        saved_at = datetime.now(timezone.utc)
        encounter_id = self.repository.save_payload(
            payload,
            encounter_timestamp=saved_at,
            patient_profile=patient_profile,
        )
        return {
            "patient_id": payload["visit"]["patient_id"],
            "visit_id": payload["visit"]["visit_id"],
            "timestamp": saved_at,
            "encounter_id": encounter_id,
        }
