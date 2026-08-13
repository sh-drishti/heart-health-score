"""
Auth endpoints and the dependencies every other route is guarded by.

Flow: POST /auth/login returns a short-lived access token plus a refresh token.
The client sends `Authorization: Bearer <access_token>`; when that 401s it calls
POST /auth/refresh once to get a new pair. The same flow works unchanged for the
React app and a native client, which is why tokens are used rather than cookies.

Accounts are not self-serve — POST /auth/users requires a clinician — because
this API grants access to other people's clinical records.
"""

from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from backend import users
from backend.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    new_refresh_token,
    verify_password,
)

router = APIRouter(tags=["auth"])

# auto_error=False so a missing header produces our own 401 with a useful
# message rather than FastAPI's bare "Not authenticated".
bearer = HTTPBearer(auto_error=False)


class LoginIn(BaseModel):
    email: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class RegisterIn(BaseModel):
    """
    Self-registration. Note the absence of `role` and `patient_id`: this always
    creates a patient, with an id the server allocates.
    """

    email: str
    password: str = Field(min_length=8)
    name: str = ""


class CreateUserIn(BaseModel):
    email: str
    password: str = Field(min_length=8)
    role: str
    name: str = ""
    patient_id: Optional[str] = None


def _session(user: Dict[str, Any]) -> Dict[str, Any]:
    """Issue a fresh token pair for a user and record the refresh side."""

    access_token, expires_in = create_access_token(user)
    refresh_plaintext, refresh_hash = new_refresh_token()
    users.store_refresh(user["_id"], refresh_hash)

    return {
        "access_token": access_token,
        "refresh_token": refresh_plaintext,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": users.public_user(user),
    }


# --- Dependencies -----------------------------------------------------------


def current_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> Dict[str, Any]:
    """Verified access-token claims. 401 if absent, malformed, or expired."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


def current_user(claims: Dict[str, Any] = Depends(current_claims)) -> Dict[str, Any]:
    """
    The account behind the token, re-read from the database.

    Costs a lookup per request but means deactivating an account takes effect
    immediately instead of when its access token happens to expire.
    """

    user = users.get_by_id(claims["sub"])
    if user is None or not user.get("active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is no longer active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*allowed: str) -> Callable[..., Dict[str, Any]]:
    """
    Dependency factory restricting a route to the given roles.

    403 rather than 401: the caller authenticated fine, the account just is not
    permitted. A patient hitting /patients/{id} lands here — the reason /me/*
    exists.
    """

    def dependency(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
        if user["role"] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This endpoint requires one of: {', '.join(allowed)}. "
                    f"Signed in as {user['role']}."
                ),
            )
        return user

    return dependency


def current_patient_id(
    user: Dict[str, Any] = Depends(require_role("patient")),
) -> str:
    """
    The patient_id a /me/* route reads. Comes from the account, never the URL,
    so a patient cannot ask for someone else's record.
    """

    patient_id = user.get("patient_id")
    if not patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not linked to a patient record",
        )
    return patient_id


def actor_name(user: Dict[str, Any]) -> str:
    """Human label for the signed-in user, stamped onto notes and encounters."""

    return user.get("name") or user["email"]


# --- Routes -----------------------------------------------------------------


@router.post(
    "/auth/login",
    summary="Sign in and get a token pair",
    responses={
        401: {"description": "Incorrect email or password."},
        403: {"description": "The account has been deactivated."},
    },
)
def login(body: LoginIn):
    user = users.get_by_email(body.email)

    # One message for both a wrong email and a wrong password, so the endpoint
    # cannot be used to enumerate which accounts exist.
    if user is None or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.get("active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )

    return _session(user)


@router.post(
    "/auth/register",
    status_code=status.HTTP_201_CREATED,
    summary="Create your own patient account",
    responses={
        409: {"description": "An account already exists for that email."},
        422: {"description": "Invalid email or password shorter than 8 characters."},
    },
)
def register(body: RegisterIn):
    """
    Open sign-up for someone assessing their own heart health. Returns a signed-in
    session, so the client does not have to log in again straight away.

    The role is always `patient` and the `patient_id` is allocated server-side —
    neither can be influenced by the request, or a caller could claim somebody
    else's record.
    """

    try:
        created = users.register_patient(
            email=body.email,
            password=body.password,
            name=body.name,
        )
    except users.EmailTaken as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return _session(created)


@router.post(
    "/auth/refresh",
    summary="Exchange a refresh token for a new pair",
    responses={401: {"description": "Refresh token is invalid, expired, or already used."}},
)
def refresh(body: RefreshIn):
    """
    Refresh tokens rotate: the presented one is revoked as it is redeemed, so
    replaying it returns 401. Store the new `refresh_token` from the response.
    """

    _plaintext, next_hash = new_refresh_token()
    user = users.consume_refresh(body.refresh_token, next_hash)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid, expired, or already used",
        )

    # consume_refresh already stored next_hash against the user, so mint the
    # access token here and hand back the matching plaintext.
    access_token, expires_in = create_access_token(user)
    return {
        "access_token": access_token,
        "refresh_token": _plaintext,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": users.public_user(user),
    }


@router.post("/auth/logout", summary="Revoke one session")
def logout(body: RefreshIn):
    """Revoke one session. Succeeds even for an unknown token — nothing to leak."""

    users.revoke_refresh(body.refresh_token)
    return {"status": "ok"}


@router.get(
    "/auth/me",
    summary="The signed-in account [any role]",
    responses={401: {"description": "Missing, malformed, or expired access token."}},
)
def read_me(user: Dict[str, Any] = Depends(current_user)):
    return {"user": users.public_user(user)}


@router.post(
    "/auth/logout-all",
    summary="Revoke every session for the caller [any role]",
    responses={401: {"description": "Missing, malformed, or expired access token."}},
)
def logout_all(user: Dict[str, Any] = Depends(current_user)):
    revoked = users.revoke_all(user["_id"])
    return {"status": "ok", "sessions_revoked": revoked}


@router.get(
    "/auth/users",
    summary="List accounts [clinician]",
    responses={
        401: {"description": "Missing, malformed, or expired access token."},
        403: {"description": "Requires: clinician."},
    },
)
def list_accounts(_: Dict[str, Any] = Depends(require_role("clinician"))):
    return {"users": users.list_users()}


@router.post(
    "/auth/users",
    status_code=status.HTTP_201_CREATED,
    summary="Create an account [clinician]",
    responses={
        401: {"description": "Missing, malformed, or expired access token."},
        403: {"description": "Requires: clinician."},
        409: {"description": "An account already exists for that email."},
        422: {"description": "Invalid role, email, password length, or patient_id linkage."},
    },
)
def create_account(
    body: CreateUserIn,
    _: Dict[str, Any] = Depends(require_role("clinician")),
):
    try:
        created = users.create_user(
            email=body.email,
            password=body.password,
            role=body.role,
            name=body.name,
            patient_id=body.patient_id,
        )
    except users.EmailTaken as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return {"user": users.public_user(created)}
