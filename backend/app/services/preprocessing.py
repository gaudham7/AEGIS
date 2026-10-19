"""
Leakage-safe preprocessing for AEGIS.

Policy:
- The target (Chiller Energy Consumption) is NEVER interpolated or fabricated.
- Feature columns may be filled only causally (forward-fill), using past
  observations from the same equipment.
- Forward-fill never crosses a detected large temporal gap.
- Missing target values remain missing and are excluded by the training
  pipeline when it requires a complete target.
"""

from typing import Dict, Any

import pandas as pd

from app.config import (
    MAX_INTERPOLATION_RUN,
    NOMINAL_SAMPLING_MINUTES,
    GAP_MULTIPLE_THRESHOLD,
    TARGET_COLUMN,
)
from app.services.ingestion import NUMERIC_COLUMNS


def _causal_fill_short_runs(
    group: pd.DataFrame,
    column: str,
    max_run: int,
) -> pd.Series:
    """Forward-fill short missing runs using only past values.

    A large timestamp gap resets the carry-forward state, so values from
    before an equipment/data outage cannot be carried into the period after it.
    """
    s = group[column].copy()

    if not s.isna().any():
        return s

    out = s.copy()
    timestamps = group["timestamp"]

    gap_after = timestamps.diff() > pd.Timedelta(
        minutes=NOMINAL_SAMPLING_MINUTES * GAP_MULTIPLE_THRESHOLD
    )

    segment_id = gap_after.fillna(False).cumsum()

    for _, idx in group.groupby(segment_id, sort=False).groups.items():
        seg = s.loc[idx]

        # Causal only: never use a future value to fill an earlier row.
        filled = seg.ffill(limit=max_run)

        out.loc[idx] = filled

    return out


def handle_missing_values(df: pd.DataFrame) -> Dict[str, Any]:
    """Apply leakage-safe missing-value handling per equipment.

    Non-target numeric features use short-run causal forward-fill.
    The target is deliberately untouched.
    """

    df = df.sort_values(
        ["equipment_id", "timestamp"]
    ).copy()

    filled_counts = {
        col: 0 for col in NUMERIC_COLUMNS
    }

    remaining_counts = {
        col: 0 for col in NUMERIC_COLUMNS
    }

    processed_frames = []

    for _, g in df.groupby("equipment_id", sort=False):
        g = g.copy()

        for col in NUMERIC_COLUMNS:
            before_na = g[col].isna()

            if col != TARGET_COLUMN:
                g[col] = _causal_fill_short_runs(
                    g,
                    col,
                    MAX_INTERPOLATION_RUN,
                )

            # TARGET_COLUMN is intentionally NEVER filled.

            after_na = g[col].isna()

            filled_counts[col] += int(
                (before_na & ~after_na).sum()
            )

            remaining_counts[col] += int(
                after_na.sum()
            )

        processed_frames.append(g)

    out = pd.concat(
        processed_frames,
        ignore_index=True,
    )

    out = (
        out
        .sort_values(["equipment_id", "timestamp"])
        .reset_index(drop=True)
    )

    report = {
        "filled_short_gap_values": filled_counts,
        "remaining_missing_values": remaining_counts,
        "target_interpolation": "disabled",
        "policy": (
            f"Non-target numeric features use causal forward-fill for at most "
            f"{MAX_INTERPOLATION_RUN} consecutive missing samples per equipment. "
            f"Large temporal gaps "
            f"(> {NOMINAL_SAMPLING_MINUTES * GAP_MULTIPLE_THRESHOLD} minutes) "
            "reset the carry-forward state. "
            f"'{TARGET_COLUMN}' is never interpolated or fabricated; missing "
            "target rows remain missing and are excluded when complete "
            "training/evaluation rows are selected."
        ),
    }

    return out, report