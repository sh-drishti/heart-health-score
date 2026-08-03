"""
Longitudinal monitoring data: HHS trend, per-domain burden trends, insights.

All assembly lives in EncounterRepository.get_monitoring_data(). This module
only makes the result safe to send over HTTP: Mongo hands back naive datetimes,
and a naive ISO string is parsed as *local* time by the browser, which would
shift every point on the x-axis. Everything else is passed through untouched.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _iso_utc(value: Any) -> Any:
    """Stamp UTC on a stored timestamp and format it ISO-8601."""

    if isinstance(value, datetime):
        aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return aware.isoformat()
    return value


def _normalise_dates(data: Dict[str, Any]) -> Dict[str, Any]:
    history = data.get("history", {})

    for point in history.get("hhs_trend", []):
        point["date"] = _iso_utc(point.get("date"))

    for series in (history.get("domain_trends") or {}).values():
        for point in series:
            point["date"] = _iso_utc(point.get("date"))

    return data


def get_monitoring(patient_id: str) -> Optional[Dict[str, Any]]:
    """
    Trend bundle for one patient, or None when no encounters are on file.

    Only patients with saved encounters have history; CSV-sourced patients
    have none.
    """

    # Imported lazily so an unreachable MONGODB_URI only breaks this endpoint,
    # not the CSV dashboard path.
    from database import EncounterRepository

    data = EncounterRepository().get_monitoring_data(patient_id)
    if data is None:
        return None

    return _normalise_dates(data)
