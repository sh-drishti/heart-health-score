"""ECG interpretation from five interval measurements.

The model and its thresholds come from the data science team as a trained
artefact — a MultiOutputClassifier over five XGBoost pipelines, trained on
PTB-XL. `interpret` reproduces their `predict_ecg` semantics exactly, including
how `status` and `abnormalities` are derived: those are their decisions, not
this layer's, and this file does not second-guess them.

Two things are added around it, both outside the model rather than inside it:

* Lazy loading. Importing sklearn, xgboost and the model costs roughly 200MB of
  RSS, and the API imports this module at startup whether or not anyone uses an
  ECG. The model loads on first interpretation and is kept after that.
* An input guard. The model has no notion of a plausible ECG and will score
  anything: all zeros returns MI at 0.85, and a mistyped heart rate of 9999
  returns NORM. Ranges are checked before the model is reached, so a typo is
  rejected rather than answered confidently.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

MODELS = Path(__file__).parent / "models"
MODEL_PATH = MODELS / "ecg_v1_hr500_official_selected.joblib"
METADATA_PATH = MODELS / "ecg_v1_hr500_official_metadata.json"

# Metadata is small and pure JSON, so it loads eagerly — the form needs the
# feature list and thresholds without paying for the model.
METADATA: dict[str, Any] = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

FEATURES: list[str] = METADATA["features"]
TARGETS: list[str] = METADATA["targets"]
THRESHOLDS: dict[str, float] = METADATA["thresholds"]
MODEL_VERSION: str = METADATA["model_version"]

# What each PTB-XL superclass stands for. The model returns bare codes.
TARGET_LABELS = {
    "NORM": "Normal ECG",
    "MI": "Myocardial infarction",
    "STTC": "ST/T change",
    "CD": "Conduction disturbance",
    "HYP": "Hypertrophy",
}

# Plausible ranges for an adult ECG. Deliberately wide — the job is to reject
# a mistyped or empty value, not to second-guess a genuine extreme.
RANGES = {
    "heart_rate": (20.0, 300.0, "bpm"),
    "pr_interval": (50.0, 500.0, "ms"),
    "qrs_duration": (40.0, 300.0, "ms"),
    "qt_interval": (200.0, 800.0, "ms"),
    "qtc_interval": (200.0, 800.0, "ms"),
}

FEATURE_LABELS = {
    "heart_rate": "Heart rate",
    "pr_interval": "PR interval",
    "qrs_duration": "QRS duration",
    "qt_interval": "QT interval",
    "qtc_interval": "QTc interval",
}

_model = None
_lock = threading.Lock()


class InvalidECG(ValueError):
    """One or more measurements are missing or outside a plausible range."""

    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__(f"{len(errors)} measurement(s) need attention")


def _load():
    """Load once, under a lock so two concurrent first requests do not both
    pay the ~200MB and the second-arriving one does not see a half-built
    object."""

    global _model
    if _model is None:
        with _lock:
            if _model is None:
                import joblib

                _model = joblib.load(MODEL_PATH)
    return _model


def model_is_loaded() -> bool:
    return _model is not None


def validate(measurements: dict[str, Any]) -> dict[str, float]:
    """Coerce and range-check. Raises InvalidECG listing every problem, rather
    than the first, so the form can mark all of them at once."""

    errors: list[dict] = []
    clean: dict[str, float] = {}

    for feature in FEATURES:
        label = FEATURE_LABELS[feature]
        low, high, unit = RANGES[feature]
        raw = measurements.get(feature)

        if raw is None or (isinstance(raw, str) and not raw.strip()):
            errors.append({"field": feature, "message": f"{label} is required."})
            continue

        try:
            value = float(raw)
        except (TypeError, ValueError):
            errors.append({"field": feature, "message": f"{label} must be a number."})
            continue

        if not (low <= value <= high):
            errors.append(
                {
                    "field": feature,
                    "message": f"{label} must be between {low:g} and {high:g} {unit}.",
                }
            )
            continue

        clean[feature] = value

    if errors:
        raise InvalidECG(errors)

    return clean


def qtc_bazett(qt_ms: float, heart_rate: float) -> float:
    """QTc by Bazett — QT / sqrt(RR), RR in seconds.

    Offered so the form can prefill a value derived from two the user has
    already entered. Verified against the reference case supplied with the
    model: QT 323 at HR 103 gives 423.2, and their sample records 423.
    """

    rr_seconds = 60.0 / heart_rate
    return round(qt_ms / (rr_seconds**0.5), 1)


def interpret(measurements: dict[str, Any]) -> dict:
    """Validate, then run the model. Output mirrors the supplied engine."""

    clean = validate(measurements)

    import pandas as pd

    model = _load()
    frame = pd.DataFrame([[clean[f] for f in FEATURES]], columns=FEATURES)
    probabilities = model.predict_proba(frame)

    predictions = {}
    abnormalities = []

    for index, target in enumerate(TARGETS):
        probability = float(probabilities[index][0][1])
        threshold = float(THRESHOLDS[target])
        positive = probability >= threshold

        predictions[target] = {
            "label": TARGET_LABELS.get(target, target),
            "probability": round(probability, 4),
            "threshold": round(threshold, 4),
            "positive": bool(positive),
        }

        if positive and target != "NORM":
            abnormalities.append(
                {
                    "type": target,
                    "label": TARGET_LABELS.get(target, target),
                    "probability": round(probability, 4),
                }
            )

    return {
        "model_version": MODEL_VERSION,
        "status": "abnormal" if abnormalities else "normal",
        "input_features": clean,
        "predictions": predictions,
        "abnormalities": abnormalities,
        # The model is multilabel with independent thresholds, so NORM can be
        # positive alongside an abnormality. Surfaced rather than hidden: a
        # reader who sees both needs to know it is a property of the model, not
        # a contradiction in their ECG.
        "norm_and_abnormal": bool(
            abnormalities and predictions.get("NORM", {}).get("positive")
        ),
    }


def form_schema() -> dict:
    """What the browser needs to render the five inputs."""

    return {
        "model_version": MODEL_VERSION,
        "fields": [
            {
                "key": feature,
                "label": FEATURE_LABELS[feature],
                "unit": RANGES[feature][2],
                "min": RANGES[feature][0],
                "max": RANGES[feature][1],
            }
            for feature in FEATURES
        ],
        "targets": [
            {"key": t, "label": TARGET_LABELS.get(t, t), "threshold": THRESHOLDS[t]}
            for t in TARGETS
        ],
    }
