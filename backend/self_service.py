"""
Patient self-service intake: a patient recording their own encounter.

Same engine, same 48-field form, same payload as the staff path in
backend/intake.py — the only differences are that the patient never supplies
their own `patient_id` or `visit_id` (both come from the server, so nobody can
write to another person's record or collide with an existing visit), and the
encounter is marked self-reported so a reviewing clinician can tell.

Repeat visits append. Nothing is ever updated in place: a second encounter is
what gives the trend charts a second point. `prefill` exists so a returning
patient starts from what they entered last time rather than a blank form, with
every measurement age advanced by the elapsed months — otherwise reusing an old
lab value would silently claim it was drawn today and overstate confidence.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend import intake
from backend.payload_convert import LABEL_TO_KEY

SELF_REPORTED = "Self-reported (patient)"


def _repo():
    from database import EncounterRepository

    return EncounterRepository()


# --- Visit ids --------------------------------------------------------------


def next_visit_id(repo: Any, patient_id: str, when: Optional[datetime] = None) -> str:
    """
    A unique, human-readable visit id for a self-recorded encounter.

    Date-based so it reads sensibly on the trend axis, with a counter suffix
    because someone may well submit twice in one day.
    """

    when = when or datetime.now(timezone.utc)
    base = f"SELF-{when:%Y-%m-%d}"

    if not repo.patient_exists(patient_id):
        return base

    taken = {
        encounter.get("visit_id")
        for encounter in repo.get_all_encounters(patient_id)
    }
    if base not in taken:
        return base

    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


# --- Prefill ----------------------------------------------------------------

_KEY_BY_LABEL = LABEL_TO_KEY


def _months_since(then: Any, now: datetime) -> float:
    """Whole-ish months between two timestamps. Mongo hands back naive values."""

    if not isinstance(then, datetime):
        return 0.0
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)

    days = (now - then).total_seconds() / 86400.0
    return max(0.0, round(days / 30.44, 1))


# Categorical answers ("Do you smoke?") are stored with months_old 0.0 by
# build_fields and have no measurement date to advance. Numeric measurements do,
# including one recorded as 0 months old — "measured today" becomes "measured a
# year ago", which is the whole point of ageing the prefill.
_CATEGORICAL_WIDGETS = ("select", "yes_no")


def _is_categorical(key: str) -> bool:
    definition = intake.FIELD_DEFS.get(key)
    return bool(definition) and definition["widget"] in _CATEGORICAL_WIDGETS


def _age_forward(key: str, months_old: Any, elapsed: float) -> Any:
    if months_old is None or _is_categorical(key):
        return months_old
    if not isinstance(months_old, (int, float)):
        return months_old
    return round(float(months_old) + elapsed, 1)


def prefill(patient_id: str) -> Optional[Dict[str, Any]]:
    """
    The patient's last submission, shaped for the intake form.

    Returns None when they have no encounters yet, which is the signal to start
    from the schema defaults. `fields` matches what POST expects, so the client
    can hand it straight to the form.
    """

    repo = _repo()
    encounter = repo.get_latest_encounter(patient_id)
    if encounter is None:
        return None

    payload = encounter.get("payload") or {}
    visit = payload.get("visit") or {}
    elapsed = _months_since(encounter.get("encounter_timestamp"), datetime.now(timezone.utc))

    fields: Dict[str, Dict[str, Any]] = {}
    for feed in payload.get("input_feeds", []):
        key = _KEY_BY_LABEL.get(feed.get("label"))
        if key is None:
            continue

        status = feed.get("status")
        if status != "Available":
            # Unknown / not measured carries no value or age to age forward.
            fields[key] = {"status": status, "value": None, "months_old": None}
            continue

        months_old = feed.get("months_old")
        fields[key] = {
            "status": status,
            "value": feed.get("value"),
            "months_old": _age_forward(key, months_old, elapsed),
        }

    return {
        "from_visit_id": encounter.get("visit_id"),
        "months_since_last_visit": elapsed,
        "visit": {
            # Age is the one thing that genuinely advances on its own.
            "age": _aged(visit.get("age"), elapsed),
            "biological_sex": visit.get("biological_sex", ""),
            "region_profile": visit.get("region_profile", ""),
            "clinical_setting": visit.get("clinical_setting", ""),
        },
        "fields": fields,
        "lpa_unit": payload.get("lpa_unit", "mg/dL"),
    }


def _aged(age: Any, elapsed_months: float) -> Any:
    """Advance a stored age by whole years only, clamped to the engine's bounds."""

    if not isinstance(age, (int, float)):
        return age
    return min(120, int(age) + int(elapsed_months // 12))


# --- Save -------------------------------------------------------------------


def save_own_encounter(
    patient_id: str,
    submission: Dict[str, Any],
    account: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Score and persist an encounter for the signed-in patient.

    The caller's `visit.patient_id` and `visit.visit_id` are ignored and
    replaced, so a patient cannot write to another record or overwrite one of
    their own past visits.
    """

    repo = _repo()
    visit = dict(submission.get("visit") or {})

    visit["patient_id"] = patient_id
    visit["visit_id"] = next_visit_id(repo, patient_id)
    visit["reviewed_by"] = SELF_REPORTED
    if not visit.get("clinical_setting"):
        visit["clinical_setting"] = SELF_REPORTED

    payload = dict(submission)
    payload["visit"] = visit

    # Contact details come from the account, not the request, so a patient
    # cannot rewrite another person's profile through this path.
    profile = dict(payload.get("patient_profile") or {})
    profile["name"] = account.get("name") or profile.get("name", "")
    contact = dict(profile.get("contact") or {})
    contact["email"] = account.get("email", contact.get("email", ""))
    profile["contact"] = contact
    payload["patient_profile"] = profile

    # visit_id is freshly generated, so a duplicate is impossible by
    # construction and the staff path's conflict check has nothing to catch.
    return intake.save(payload, allow_duplicate_visit=True)
