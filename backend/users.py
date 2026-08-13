"""
Accounts and sessions in MongoDB: the `users` and `refresh_tokens` collections.

These are the only collections this project's API owns outright. `patients`,
`encounters` and `clinical_notes` keep their existing owners (database.py and
backend/notes.py) and are not touched here — an account references a patient by
the same `patient_id` string those collections already key on, so no migration
is needed.

Follows backend/notes.py in importing the connection lazily, so an unreachable
MONGODB_URI surfaces as a failing request rather than an import-time crash.
"""

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from backend.security import hash_password, hash_refresh_token, refresh_expiry

USERS = "users"
REFRESH_TOKENS = "refresh_tokens"

ROLES = ("clinician", "staff", "patient")


class EmailTaken(Exception):
    """Raised when create_user hits the unique index on email."""


def _db():
    from database import db

    return db


def ensure_indexes() -> None:
    """
    Create the indexes the auth flow depends on. Idempotent.

    The unique index on email is the actual guarantee against duplicate
    accounts; the application-level check in create_user only exists to turn
    the resulting error into a clean 409.
    """

    db = _db()
    db[USERS].create_index("email", unique=True)
    db[USERS].create_index("patient_id")
    db[REFRESH_TOKENS].create_index("token_hash", unique=True)
    db[REFRESH_TOKENS].create_index("user_id")


# --- Accounts ---------------------------------------------------------------


def public_user(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Account fields safe to return over HTTP. Never includes the hash."""

    return {
        "id": str(doc["_id"]),
        "email": doc["email"],
        "name": doc.get("name", ""),
        "role": doc["role"],
        "patient_id": doc.get("patient_id"),
    }


def get_by_email(email: str) -> Optional[Dict[str, Any]]:
    return _db()[USERS].find_one({"email": email.strip().lower()})


def get_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    try:
        oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return None
    return _db()[USERS].find_one({"_id": oid})


def create_user(
    email: str,
    password: str,
    role: str,
    name: str = "",
    patient_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an account. Raises ValueError on bad input, EmailTaken on conflict.

    A patient account without a patient_id could never resolve /me/*, and a
    patient_id on a clinician would silently widen what their token grants, so
    both are rejected rather than normalised.
    """

    if role not in ROLES:
        raise ValueError(f"role must be one of {', '.join(ROLES)}")

    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("A valid email is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    if role == "patient":
        if not patient_id:
            raise ValueError("A patient account must be linked to a patient_id")
    elif patient_id:
        raise ValueError("Only patient accounts may be linked to a patient_id")

    doc = {
        "email": email,
        "password_hash": hash_password(password),
        "role": role,
        "name": name.strip(),
        "patient_id": patient_id,
        "active": True,
        "created_at": datetime.now(timezone.utc),
    }

    try:
        result = _db()[USERS].insert_one(doc)
    except DuplicateKeyError:
        raise EmailTaken(f"An account already exists for {email}")

    doc["_id"] = result.inserted_id
    return doc


def list_users() -> List[Dict[str, Any]]:
    return [public_user(doc) for doc in _db()[USERS].find().sort("created_at", 1)]


def _new_patient_id() -> str:
    """
    Mint an unused patient_id for a self-registering user.

    Deliberately server-side: if a client could choose this, anyone could
    register claiming an existing id and read that person's record, which would
    defeat the whole point of resolving /me/* from the token.
    """

    users = _db()[USERS]
    for _attempt in range(10):
        candidate = f"HHS-U-{secrets.token_hex(4).upper()}"
        # The users collection is the authority on which ids are claimed; the
        # patients collection also holds clinician-created ids, so check both.
        if users.find_one({"patient_id": candidate}) is None:
            from database import patients_collection

            if patients_collection.find_one({"patient_id": candidate}) is None:
                return candidate

    raise RuntimeError("Could not allocate a patient id; try again")


def register_patient(email: str, password: str, name: str = "") -> Dict[str, Any]:
    """
    Self-registration. Always creates a `patient` account with a fresh
    patient_id — never one the caller supplied.
    """

    return create_user(
        email=email,
        password=password,
        role="patient",
        name=name,
        patient_id=_new_patient_id(),
    )


# --- Sessions ---------------------------------------------------------------


def store_refresh(user_id: Any, token_hash: str) -> None:
    _db()[REFRESH_TOKENS].insert_one({
        "user_id": str(user_id),
        "token_hash": token_hash,
        "created_at": datetime.now(timezone.utc),
        "expires_at": refresh_expiry(),
        "revoked_at": None,
    })


def consume_refresh(plaintext: str, new_hash: str) -> Optional[Dict[str, Any]]:
    """
    Rotate a refresh token: revoke the presented one and record its successor.

    Returns the owning user document, or None if the token is unknown, already
    used, revoked, expired, or belongs to a deactivated account. The revoke and
    the lookup are one atomic update so two concurrent refreshes cannot both
    succeed with the same token.
    """

    db = _db()
    now = datetime.now(timezone.utc)

    session = db[REFRESH_TOKENS].find_one_and_update(
        {
            "token_hash": hash_refresh_token(plaintext),
            "revoked_at": None,
            "expires_at": {"$gt": now},
        },
        {"$set": {"revoked_at": now}},
    )
    if session is None:
        return None

    user = get_by_id(session["user_id"])
    if user is None or not user.get("active", True):
        return None

    store_refresh(session["user_id"], new_hash)
    return user


def revoke_refresh(plaintext: str) -> bool:
    """Revoke a single refresh token. Used by logout."""

    result = _db()[REFRESH_TOKENS].update_one(
        {"token_hash": hash_refresh_token(plaintext), "revoked_at": None},
        {"$set": {"revoked_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count > 0


def revoke_all(user_id: Any) -> int:
    """Revoke every live session for a user. Sign out on all devices."""

    result = _db()[REFRESH_TOKENS].update_many(
        {"user_id": str(user_id), "revoked_at": None},
        {"$set": {"revoked_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count
