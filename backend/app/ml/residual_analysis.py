"""
Contextual anomaly scoring based on XGBoost prediction residuals.

Pipeline:
    actual_energy - expected_energy (XGBoost prediction) = residual
    residual -> per-equipment robust z-score (MAD-based) -> "unusualness"

CRITICAL correctness requirement (explicitly required by the project spec):
Residual calibration (the median / MAD used to convert a residual into an
"unusualness" score) MUST be computed from genuinely held-out predictions,
never from in-sample training predictions. Training residuals are
artificially small/optimistic (the model has already seen those exact
rows), which would make the anomaly scores systematically wrong.

Concretely: we calibrate median/MAD per equipment_id using the VALIDATION
split's residuals (validation rows were never used to fit the model's
parameters). Those same statistics are then applied, unchanged, when
scoring the validation set itself, the test set, and any future inference
data. This mirrors how the scoring would be used in production: a fixed,
pre-computed normal-behaviour baseline applied to *new* observations.
"""
from typing import Dict, Any
import numpy as np
import pandas as pd

MAD_CONSTANT = 0.6745  # scales MAD to be comparable to std dev for normal data
MIN_SAMPLES_FOR_PER_EQUIPMENT_STATS = 20


def calibrate_residual_stats(val_equipment_ids: pd.Series, val_residuals: pd.Series) -> Dict[str, Any]:
    """Compute per-equipment median and MAD of residuals using held-out
    (validation) predictions only. Falls back to a global statistic for any
    equipment with too few validation samples to estimate robust stats."""
    df = pd.DataFrame({"equipment_id": val_equipment_ids.values, "residual": val_residuals.values})

    global_median = float(df["residual"].median())
    global_mad = float((df["residual"] - global_median).abs().median())
    if global_mad == 0:
        global_mad = float(df["residual"].std()) or 1.0

    per_equipment = {}
    for eq, g in df.groupby("equipment_id"):
        if len(g) >= MIN_SAMPLES_FOR_PER_EQUIPMENT_STATS:
            median = float(g["residual"].median())
            mad = float((g["residual"] - median).abs().median())
            if mad == 0:
                mad = float(g["residual"].std()) or global_mad
            per_equipment[eq] = {"median": median, "mad": mad, "n_calibration_samples": int(len(g))}
        else:
            per_equipment[eq] = {
                "median": global_median,
                "mad": global_mad,
                "n_calibration_samples": int(len(g)),
                "note": "insufficient validation samples; using global fallback statistics",
            }

    return {
        "global": {"median": global_median, "mad": global_mad},
        "per_equipment": per_equipment,
        "calibration_source": "validation_split_holdout_predictions",
    }


def score_residuals(equipment_ids: pd.Series, residuals: pd.Series, stats: Dict[str, Any]) -> np.ndarray:
    """Apply pre-computed (held-out-calibrated) per-equipment median/MAD to
    turn residuals into a robust "unusualness" z-score."""
    per_eq = stats["per_equipment"]
    g_median, g_mad = stats["global"]["median"], stats["global"]["mad"]

    medians = equipment_ids.map(lambda e: per_eq.get(e, {}).get("median", g_median)).astype(float)
    mads = equipment_ids.map(lambda e: per_eq.get(e, {}).get("mad", g_mad)).astype(float)
    mads = mads.replace(0, g_mad if g_mad else 1.0)

    z = MAD_CONSTANT * (residuals.values - medians.values) / mads.values
    return z
