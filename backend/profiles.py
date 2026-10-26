"""
A patient's own baseline profile: what the mobile app's onboarding screens
collect — sex, date of birth, height and weight, sleep and activity habits, and
a first set of vitals.

One document per patient in `patient_profiles`, a collection this API owns.
Kept apart from `patients` (database.py's) and from encounters on purpose: this
is what someone tells us about themselves when they sign up, not a scored
assessment, and it is never fed to the engine.

Two fields are deliberately not stored here:

  name  lives on the account. The onboarding screen edits it, but saving one
        here as well would give the same person two names that drift apart.
  age   is derived from date_of_birth on every read. A stored age is wrong a
        year later; a birth date never is.

Follows backend/notes.py in importing the connection lazily, so an unreachable
MONGODB_URI surfaces as a failing request rather than an import-time crash.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.timeutil import iso_utc

COLLECTION = "patient_profiles"

# The same strings the intake form uses, so a profile can seed an encounter
# without translation. The app may show only the first two.
BiologicalSex = Literal["Male", "Female", "Intersex / other", "Unknown"]

# Stable codes rather than the app's display text, so rewording a button never
# changes what is stored. Each is recorded alongside an optional exact figure:
# someone may pick a band, type a number, or both.
SleepOption = Literal["under_6", "6_to_8", "8_to_10", "over_10"]
ActivityOption = Literal[
    "mostly_sitting", "often_standing", "regularly_walking", "physically_intense"
]

# Bounds match backend/intake_schema.py where the field exists there.
MIN_AGE, MAX_AGE = 1, 120
VITALS = ("sbp", "dbp", "resting_hr")


class ProfileIn(BaseModel):
    """
    The whole profile. Sex, date of birth, weight and height are required: they
    come from the one onboarding screen that cannot be skipped. Everything else
    is nullable, because the Daily Activity and Vitals screens can be.
    """

    name: Optional[str] = Field(
        default=None,
        description=(
            "Updates the account's name. Omit or leave blank to keep it. Not "
            "stored on the profile."
        ),
    )
    biological_sex: BiologicalSex
    date_of_birth: date = Field(description="YYYY-MM-DD. Age is derived from it.")
    weight_kg: float = Field(ge=5, le=300)
    height_cm: float = Field(ge=50, le=250)

    sleep_option: Optional[SleepOption] = None
    sleep_hours: Optional[float] = Field(
        default=None, ge=0, le=24, description="Hours of sleep per night."
    )
    activity_option: Optional[ActivityOption] = None
    activity_hours_per_day: Optional[float] = Field(default=None, ge=0, le=24)

    sbp: Optional[int] = Field(default=None, ge=70, le=260, description="Systolic, mmHg.")
    dbp: Optional[int] = Field(default=None, ge=40, le=160, description="Diastolic, mmHg.")
    resting_hr: Optional[int] = Field(default=None, ge=40, le=180, description="Beats per minute.")

    @field_validator("date_of_birth")
    @classmethod
    def _plausible_birth_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        if not MIN_AGE <= age_on(value, date.today()) <= MAX_AGE:
            raise ValueError(f"age must be between {MIN_AGE} and {MAX_AGE}")
        return value

    @model_validator(mode="after")
    def _blood_pressure_pair(self) -> "ProfileIn":
        # One half of a blood pressure reading means nothing on its own.
        if (self.sbp is None) != (self.dbp is None):
            raise ValueError("sbp and dbp must be given together")
        if self.sbp is not None and self.dbp is not None and self.sbp <= self.dbp:
            raise ValueError("sbp must be higher than dbp")
        return self


class ProfilePatch(BaseModel):
    """
    Any subset of the profile. A field sent as null is cleared — which is how a
    skipped answer is undone — but the four required fields cannot be cleared.
    The merged result is validated as a whole, so a patch cannot leave half a
    blood pressure reading behind.
    """

    name: Optional[str] = None
    biological_sex: Optional[BiologicalSex] = None
    date_of_birth: Optional[date] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    sleep_option: Optional[SleepOption] = None
    sleep_hours: Optional[float] = None
    activity_option: Optional[ActivityOption] = None
    activity_hours_per_day: Optional[float] = None
    sbp: Optional[int] = None
    dbp: Optional[int] = None
    resting_hr: Optional[int] = None


class ProfileMissing(Exception):
    """A patch arrived before the profile was ever created."""


def _collection():
    from database import db

    return db[COLLECTION]


def ensure_indexes() -> None:
    """One profile per patient, enforced by the database rather than by hope."""

    _collection().create_index("patient_id", unique=True)


# --- Derived values ---------------------------------------------------------


def age_on(born: date, today: date) -> int:
    """Whole years, counting a birthday not yet reached this year."""

    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _bmi(weight_kg: Any, height_cm: Any) -> Optional[float]:
    if not weight_kg or not height_cm:
        return None
    metres = float(height_cm) / 100.0
    return round(float(weight_kg) / (metres * metres), 1)


def _public(doc: Dict[str, Any], name: str) -> Dict[str, Any]:
    born = date.fromisoformat(doc["date_of_birth"])
    return {
        "name": name,
        "biological_sex": doc["biological_sex"],
        "date_of_birth": doc["date_of_birth"],
        "age": age_on(born, date.today()),
        "weight_kg": doc["weight_kg"],
        "height_cm": doc["height_cm"],
        "bmi": _bmi(doc["weight_kg"], doc["height_cm"]),
        "sleep_option": doc.get("sleep_option"),
        "sleep_hours": doc.get("sleep_hours"),
        "activity_option": doc.get("activity_option"),
        "activity_hours_per_day": doc.get("activity_hours_per_day"),
        "sbp": doc.get("sbp"),
        "dbp": doc.get("dbp"),
        "resting_hr": doc.get("resting_hr"),
        "vitals_recorded_at": iso_utc(doc.get("vitals_recorded_at")) or None,
        "created_at": iso_utc(doc.get("created_at")),
        "updated_at": iso_utc(doc.get("updated_at")),
    }


# --- Read and write ---------------------------------------------------------


def get_profile(patient_id: str, name: str) -> Optional[Dict[str, Any]]:
    """The patient's profile, or None if onboarding has not been completed."""

    doc = _collection().find_one({"patient_id": patient_id}, {"_id": 0})
    return None if doc is None else _public(doc, name)


def _stored_fields(profile: ProfileIn) -> Dict[str, Any]:
    data = profile.model_dump(exclude={"name"})
    # Mongo has no date type, only datetime; an ISO string keeps it a date.
    data["date_of_birth"] = profile.date_of_birth.isoformat()
    return data


def _write(
    patient_id: str,
    profile: ProfileIn,
    existing: Optional[Dict[str, Any]],
    name: str,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    fields = _stored_fields(profile)

    # When the vitals were taken, not when the profile was last touched: editing
    # a weight next month must not make a three-month-old blood pressure look
    # fresh. Only a change to the readings themselves moves it.
    before = tuple((existing or {}).get(key) for key in VITALS)
    after = tuple(fields[key] for key in VITALS)
    if all(value is None for value in after):
        fields["vitals_recorded_at"] = None
    elif after != before:
        fields["vitals_recorded_at"] = now
    else:
        fields["vitals_recorded_at"] = (existing or {}).get("vitals_recorded_at")

    fields["updated_at"] = now
    _collection().update_one(
        {"patient_id": patient_id},
        {"$set": fields, "$setOnInsert": {"patient_id": patient_id, "created_at": now}},
        upsert=True,
    )
    return _public(_collection().find_one({"patient_id": patient_id}, {"_id": 0}), name)


def save_profile(patient_id: str, profile: ProfileIn, name: str) -> Dict[str, Any]:
    """Create or replace the whole profile. `name` is the account's, for the response."""

    existing = _collection().find_one({"patient_id": patient_id}, {"_id": 0})
    return _write(patient_id, profile, existing, name)


def merge_patch(patient_id: str, patch: ProfilePatch) -> ProfileIn:
    """
    The stored profile with a patch applied, validated as a whole.

    Raises ProfileMissing if there is nothing to patch, and pydantic's
    ValidationError if the result is not a valid profile. Separate from saving so
    the route can reject a bad patch before it touches the account's name.
    """

    existing = _collection().find_one({"patient_id": patient_id}, {"_id": 0})
    if existing is None:
        raise ProfileMissing()

    merged = {key: value for key, value in existing.items() if key in ProfileIn.model_fields}
    merged.update(patch.model_dump(exclude_unset=True))
    return ProfileIn.model_validate(merged)
