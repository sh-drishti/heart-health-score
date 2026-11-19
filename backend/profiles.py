"""
A patient's own baseline profile: what the mobile app's onboarding screens
collect — sex, date of birth, height and weight, sleep and activity habits, and
a first set of vitals.

One document per patient in `patient_profiles`, a collection this API owns.
Kept apart from `patients` (database.py's) and from encounters on purpose: this
is what someone tells us about themselves when they sign up, not a scored
assessment, and it is never fed to the engine.

Some fields are deliberately not stored here:

  name  lives on the account. The onboarding screen edits it, but saving one
        here as well would give the same person two names that drift apart.
  age   is derived from date_of_birth on every read. A stored age is wrong a
        year later; a birth date never is.
  contact, emergency_contact, notification_preferences
        live on the patient's record in `patients`, which is where the
        notification service reads them. The profile routes read and write
        them there, so there is only ever one copy.

Follows backend/notes.py in importing the connection lazily, so an unreachable
MONGODB_URI surfaces as a failing request rather than an import-time crash.
"""

from datetime import date, datetime, timezone
from typing import Annotated, Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from backend.timeutil import iso_utc

COLLECTION = "patient_profiles"

# The same strings the intake form uses, so a profile can seed an encounter
# without translation. The app may show only the first two.
BiologicalSex = Literal["Male", "Female", "Intersex / other", "Unknown"]

# Stable codes rather than the app's display text, so rewording a button never
# changes what is stored. The app offers only these options, with no free-text
# hours: one code per question, or null if the screen was skipped.
SleepOption = Literal["under_6", "6_to_8", "8_to_10", "over_10"]
ActivityOption = Literal[
    "mostly_sitting", "often_standing", "regularly_walking", "physically_intense"
]

# Bounds match backend/intake_schema.py where the field exists there.
MIN_AGE, MAX_AGE = 1, 120
VITALS = ("sbp", "dbp", "resting_hr")


# --- Contact details --------------------------------------------------------
#
# The same shapes the intake form's `patient_profile` uses (SubmissionIn in
# backend/main.py imports these), so both paths store identical documents.

Email = Annotated[str, StringConstraints(strip_whitespace=True, max_length=254)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, max_length=32)]


class ContactIn(BaseModel):
    email: Email = Field(
        default="",
        description=(
            "Where to send this patient's emails. Editable, and separate from "
            "the email they sign in with. Send an empty string to clear."
        ),
    )
    phone: Phone = Field(default="", description="Send an empty string to clear.")


class NotificationPreferencesIn(BaseModel):
    # Off unless the patient turns them on.
    email: bool = False
    push: bool = False


class EmergencyContactIn(BaseModel):
    name: str = Field(default="", max_length=120)
    relation: str = Field(default="", max_length=60)
    contact: ContactIn = Field(default_factory=ContactIn)


CONTACT_SECTIONS = ("contact", "emergency_contact", "notification_preferences")

_EMPTY_SECTIONS: Dict[str, Dict[str, Any]] = {
    "contact": ContactIn().model_dump(),
    "emergency_contact": EmergencyContactIn().model_dump(),
    "notification_preferences": NotificationPreferencesIn().model_dump(),
}

_CONTACT_NOTE = (
    "Only the keys you send are changed; anything left out keeps its saved "
    "value. Send null to clear the whole section."
)


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
    activity_option: Optional[ActivityOption] = None

    sbp: Optional[int] = Field(default=None, ge=70, le=260, description="Systolic, mmHg.")
    dbp: Optional[int] = Field(default=None, ge=40, le=160, description="Diastolic, mmHg.")
    resting_hr: Optional[int] = Field(default=None, ge=40, le=180, description="Beats per minute.")

    contact: Optional[ContactIn] = Field(default=None, description=_CONTACT_NOTE)
    emergency_contact: Optional[EmergencyContactIn] = Field(default=None, description=_CONTACT_NOTE)
    notification_preferences: Optional[NotificationPreferencesIn] = Field(
        default=None, description=_CONTACT_NOTE
    )

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

    The three contact sections change key by key: `{"contact": {"phone": "…"}}`
    updates the phone and leaves the saved email alone.
    """

    name: Optional[str] = None
    biological_sex: Optional[BiologicalSex] = None
    date_of_birth: Optional[date] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    sleep_option: Optional[SleepOption] = None
    activity_option: Optional[ActivityOption] = None
    sbp: Optional[int] = None
    dbp: Optional[int] = None
    resting_hr: Optional[int] = None
    contact: Optional[ContactIn] = None
    emergency_contact: Optional[EmergencyContactIn] = None
    notification_preferences: Optional[NotificationPreferencesIn] = None


class ProfileMissing(Exception):
    """A patch arrived before the profile was ever created."""


def _collection():
    from database import db

    return db[COLLECTION]


def _patients():
    from database import patients_collection

    return patients_collection


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


def _public(doc: Dict[str, Any], name: str, contact: Dict[str, Any]) -> Dict[str, Any]:
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
        "activity_option": doc.get("activity_option"),
        "sbp": doc.get("sbp"),
        "dbp": doc.get("dbp"),
        "resting_hr": doc.get("resting_hr"),
        "vitals_recorded_at": iso_utc(doc.get("vitals_recorded_at")) or None,
        **contact,
        "created_at": iso_utc(doc.get("created_at")),
        "updated_at": iso_utc(doc.get("updated_at")),
    }


# --- Contact sections, on the patient record --------------------------------


def _filled(stored: Any, empty: Dict[str, Any]) -> Dict[str, Any]:
    """`stored` laid over the empty shape, so every key is always present."""

    stored = stored if isinstance(stored, dict) else {}
    out = {}
    for key, blank in empty.items():
        value = stored.get(key, blank)
        out[key] = _filled(value, blank) if isinstance(blank, dict) else value
    return out


def saved_contact_sections(patient_id: str) -> Dict[str, Dict[str, Any]]:
    """
    The contact sections that exist on the patient record, as stored. A section
    that was never saved is absent, which is how the visit route knows to fall
    back to what the request carried.
    """

    doc = _patients().find_one(
        {"patient_id": patient_id}, {"_id": 0, **{s: 1 for s in CONTACT_SECTIONS}}
    ) or {}
    return {s: doc[s] for s in CONTACT_SECTIONS if isinstance(doc.get(s), dict)}


def get_contact(patient_id: str) -> Dict[str, Dict[str, Any]]:
    """All three sections, with blanks (and notifications off) for anything unsaved."""

    saved = saved_contact_sections(patient_id)
    return {s: _filled(saved.get(s), _EMPTY_SECTIONS[s]) for s in CONTACT_SECTIONS}


def _dotted(prefix: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """{"a": {"b": 1}} under "x" becomes {"x.a.b": 1}: one $set per sent key."""

    out: Dict[str, Any] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}"
        if isinstance(value, dict):
            out.update(_dotted(path, value))
        else:
            out[path] = value
    return out


def _contact_updates(profile: ProfileIn) -> Dict[str, Any]:
    """
    The $set for the contact sections the request actually sent. Unsent
    sections, and unsent keys within a sent section, are left untouched; a
    section sent as null is reset to blank.
    """

    updates: Dict[str, Any] = {}
    for section in CONTACT_SECTIONS:
        if section not in profile.model_fields_set:
            continue
        value = getattr(profile, section)
        if value is None:
            updates[section] = _EMPTY_SECTIONS[section]
        else:
            updates.update(_dotted(section, value.model_dump(exclude_unset=True)))
    return updates


def _save_contact(patient_id: str, profile: ProfileIn) -> None:
    updates = _contact_updates(profile)
    if not updates:
        return
    # A dotted path cannot be set inside a field that holds null, so repair any
    # such section to its empty shape first. Records written by the intake path
    # always hold objects; this only guards against hand-edited ones.
    for section in {key.split(".")[0] for key in updates if "." in key}:
        _patients().update_one(
            {"patient_id": patient_id, section: None},
            {"$set": {section: _EMPTY_SECTIONS[section]}},
        )
    _patients().update_one(
        {"patient_id": patient_id},
        {
            "$set": updates,
            # The same fields database.py's upsert_patient sets on a new record.
            "$setOnInsert": {"created_at": datetime.now(timezone.utc), "active": True},
        },
        upsert=True,
    )


# --- Read and write ---------------------------------------------------------


def get_profile(patient_id: str, name: str) -> Optional[Dict[str, Any]]:
    """The patient's profile, or None if onboarding has not been completed."""

    doc = _collection().find_one({"patient_id": patient_id}, {"_id": 0})
    return None if doc is None else _public(doc, name, get_contact(patient_id))


def _stored_fields(profile: ProfileIn) -> Dict[str, Any]:
    data = profile.model_dump(exclude={"name", *CONTACT_SECTIONS})
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
    _save_contact(patient_id, profile)
    return _public(
        _collection().find_one({"patient_id": patient_id}, {"_id": 0}),
        name,
        get_contact(patient_id),
    )


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
