"""
Password hashing and token minting. Pure functions: no database, no FastAPI.

Access tokens are short-lived JWTs the API verifies on every request. Refresh
tokens are opaque random strings — only their SHA-256 hash is stored, so a
database leak does not hand over usable sessions, and revoking one is a matter
of marking a row rather than maintaining a JWT denylist.
"""

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MIN = int(os.getenv("ACCESS_TOKEN_TTL_MIN", "30"))
REFRESH_TOKEN_TTL_DAYS = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "30"))

if not JWT_SECRET:
    # Falling back to a built-in default would sign tokens anyone could forge,
    # and the failure would be invisible. Refuse to start instead.
    raise RuntimeError(
        "JWT_SECRET is not set. Add it to .env (see .env.example); generate one "
        "with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
    )


class TokenError(Exception):
    """Raised when an access token is missing, malformed, or expired."""


# --- Passwords --------------------------------------------------------------

# bcrypt hashes at most 72 bytes and bcrypt 5.x raises rather than truncating.
# Pre-hashing keeps long passphrases usable and makes the input a fixed length.
def _prepare(password: str) -> bytes:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode("utf-8"))
    except ValueError:
        # Stored hash is not a valid bcrypt digest; treat as a failed login.
        return False


# --- Access tokens ----------------------------------------------------------


def create_access_token(user: Dict[str, Any]) -> Tuple[str, int]:
    """
    Sign an access token for a user document.

    Returns (token, expires_in_seconds) so a client knows when to refresh
    without having to decode the token itself.
    """

    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=ACCESS_TOKEN_TTL_MIN)

    claims: Dict[str, Any] = {
        "sub": str(user["_id"]),
        "role": user["role"],
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }

    # Only patients are bound to a record; `pid` is what /me/* resolves against.
    if user.get("patient_id"):
        claims["pid"] = user["patient_id"]

    token = jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, ACCESS_TOKEN_TTL_MIN * 60


def decode_access_token(token: str) -> Dict[str, Any]:
    """Verify signature and expiry, returning the claims. Raises TokenError."""

    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise TokenError("Access token has expired")
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"Invalid access token: {exc}")

    # A refresh token is opaque, so this cannot currently be confused for one,
    # but checking keeps that true if the refresh format ever changes.
    if claims.get("typ") != "access":
        raise TokenError("Not an access token")

    return claims


# --- Refresh tokens ---------------------------------------------------------


def new_refresh_token() -> Tuple[str, str]:
    """Return (plaintext, sha256_hash). Only the hash is ever stored."""

    plaintext = secrets.token_urlsafe(48)
    return plaintext, hash_refresh_token(plaintext)


def hash_refresh_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
