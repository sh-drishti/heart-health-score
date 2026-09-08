"""HTTP surface for ECG interpretation.

Mounted under /api/v1/ecg and requires a signed-in user, like everything else
on that prefix. Nothing is persisted — a request goes in, a reading comes back,
and no record of it is kept.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend import auth
from ecg import engine

router = APIRouter(prefix="/api/v1/ecg", tags=["ecg"])


class ECGIn(BaseModel):
    heart_rate: Optional[float] = None
    pr_interval: Optional[float] = None
    qrs_duration: Optional[float] = None
    qt_interval: Optional[float] = None
    qtc_interval: Optional[float] = None


@router.get("/schema", summary="The five measurements and what the model reports")
def get_schema(user=Depends(auth.current_user)):
    return engine.form_schema()


@router.post("/interpret", summary="Interpret one set of measurements")
def interpret(payload: ECGIn, user=Depends(auth.current_user)) -> dict[str, Any]:
    try:
        return engine.interpret(payload.model_dump())
    except engine.InvalidECG as invalid:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"message": "Check these measurements.", "errors": invalid.errors},
        )


@router.get("/qtc", summary="QTc by Bazett, for prefilling the form")
def qtc(qt_interval: float, heart_rate: float, user=Depends(auth.current_user)):
    if heart_rate <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Heart rate must be above zero.")
    return {"qtc_interval": engine.qtc_bazett(qt_interval, heart_rate)}
