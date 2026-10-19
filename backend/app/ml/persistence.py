"""
Persistence / grouping: a single unusual observation is not automatically
as significant as a sustained deviation. Consecutive abnormal observations
(per equipment, in chronological order) are grouped into "abnormal
periods", and severity is derived from a combination of:
  - magnitude   (how large the residual / unusualness score is)
  - persistence (how many consecutive samples / how long the period lasts)
  - recurrence  (how many separate abnormal periods this equipment has had)

This module makes no claim that persistence proves a physical failure -
it only describes observed statistical behaviour of the model's residuals.
"""
from typing import List, Dict, Any
import uuid
import numpy as np
import pandas as pd

from app.config import ANOMALY_Z_THRESHOLD, PERSISTENCE_MAX_GAP_SAMPLES, NOMINAL_SAMPLING_MINUTES


def flag_abnormal_observations(df: pd.DataFrame, z_col: str = "unusualness_score") -> pd.DataFrame:
    df = df.copy()
    df["is_abnormal"] = df[z_col].abs() >= ANOMALY_Z_THRESHOLD
    return df


def group_abnormal_periods(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Group consecutive abnormal observations (per equipment, sorted by
    time) into periods, tolerating up to PERSISTENCE_MAX_GAP_SAMPLES normal
    samples in between so brief single-sample recoveries don't artificially
    split one sustained event into many."""
    periods: List[Dict[str, Any]] = []

    for eq, g in df.groupby("equipment_id", sort=False):
        g = g.sort_values("timestamp").reset_index(drop=True)
        abnormal_idx = g.index[g["is_abnormal"]].tolist()
        if not abnormal_idx:
            continue

        # cluster indices allowing small gaps
        clusters = []
        current = [abnormal_idx[0]]
        for idx in abnormal_idx[1:]:
            if idx - current[-1] <= PERSISTENCE_MAX_GAP_SAMPLES + 1:
                current.append(idx)
            else:
                clusters.append(current)
                current = [idx]
        clusters.append(current)

        # count recurrence: total number of periods for this equipment overall
        recurrence_count = len(clusters)

        for cluster in clusters:
            start_i, end_i = cluster[0], cluster[-1]
            segment = g.iloc[start_i:end_i + 1]
            all_abnormal_in_segment = g.iloc[cluster]

            magnitude = float(all_abnormal_in_segment["unusualness_score"].abs().mean())
            max_magnitude = float(all_abnormal_in_segment["unusualness_score"].abs().max())
            duration_samples = int(end_i - start_i + 1)
            # A period spans `duration_samples` samples, each covering one
            # nominal sampling interval. Using the raw timestamp gap
            # (last - first) undercounts by one interval, and is exactly
            # zero for a single-observation period even though that
            # observation still represents ~NOMINAL_SAMPLING_MINUTES of
            # abnormal operation. Add one interval to the raw gap so a
            # lone observation is reported as one sample's worth of time
            # rather than "0 minutes".
            raw_span_minutes = float((segment["timestamp"].iloc[-1] - segment["timestamp"].iloc[0]).total_seconds() / 60)
            duration_minutes = raw_span_minutes + NOMINAL_SAMPLING_MINUTES

            severity_score = _severity_score(magnitude, max_magnitude, duration_samples, recurrence_count)

            periods.append({
                "period_id": str(uuid.uuid4())[:8],
                "equipment_id": eq,
                "start_time": segment["timestamp"].iloc[0].isoformat(),
                "end_time": segment["timestamp"].iloc[-1].isoformat(),
                "duration_minutes": duration_minutes,
                "n_abnormal_observations": int(len(cluster)),
                "n_observations_in_period": int(len(segment)),
                "avg_unusualness": round(magnitude, 3),
                "max_unusualness": round(max_magnitude, 3),
                "avg_residual": round(float(all_abnormal_in_segment["residual"].mean()), 3),
                "avg_actual_energy": round(float(segment["actual_energy"].mean()), 3),
                "avg_expected_energy": round(float(segment["expected_energy"].mean()), 3),
                "severity_score": round(severity_score, 3),
                "severity_label": _severity_label(severity_score),
                "recurrence_count_for_equipment": recurrence_count,
                "observation_rows": all_abnormal_in_segment.to_dict("records"),
            })

    periods.sort(key=lambda p: p["severity_score"], reverse=True)
    return periods


def _severity_score(magnitude: float, max_magnitude: float, duration_samples: int, recurrence_count: int) -> float:
    """Combine magnitude, persistence and recurrence into a single 0-100
    priority score. Weighted heuristic, not a physical certainty measure."""
    # normalize components with soft caps so a single extreme value can't
    # dominate arbitrarily
    magnitude_component = min(max_magnitude / 10.0, 1.0) * 50  # up to 50 pts
    persistence_component = min(duration_samples / 10.0, 1.0) * 35  # up to 35 pts
    recurrence_component = min((recurrence_count - 1) / 5.0, 1.0) * 15  # up to 15 pts
    return magnitude_component + persistence_component + recurrence_component


def _severity_label(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"