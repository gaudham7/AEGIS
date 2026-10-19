"""
Time-aware feature engineering for AEGIS.

Leakage-prevention rules:
- Each equipment_id is treated as its own chronological series.
- Lags and rolling statistics use strictly past observations.
- Large temporal gaps split an equipment series into independent contiguous
  segments, so historical features never carry stale values across outages.
- equipment_id is one-hot encoded and never treated as a numeric magnitude.
- The target itself is never used directly as an input feature; only past
  target values are used.
"""

from typing import List, Tuple

import pandas as pd
import numpy as np

from app.config import (
    TARGET_COLUMN,
    OPERATIONAL_COLUMNS,
    ENVIRONMENTAL_COLUMNS,
    LAG_STEPS,
    ROLLING_WINDOWS,
    NOMINAL_SAMPLING_MINUTES,
    GAP_MULTIPLE_THRESHOLD,
)


HISTORICAL_SOURCE_COLUMNS = [
    TARGET_COLUMN,
    "Building Load (RT)",
    "Chilled Water Rate (L/sec)",
]


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    ts = df["timestamp"]

    df["hour"] = ts.dt.hour
    df["day_of_week"] = ts.dt.dayofweek
    df["month"] = ts.dt.month

    df["is_weekend"] = (
        ts.dt.dayofweek >= 5
    ).astype(int)

    # Cyclic time encodings
    df["hour_sin"] = np.sin(
        2 * np.pi * df["hour"] / 24
    )

    df["hour_cos"] = np.cos(
        2 * np.pi * df["hour"] / 24
    )

    df["dow_sin"] = np.sin(
        2 * np.pi * df["day_of_week"] / 7
    )

    df["dow_cos"] = np.cos(
        2 * np.pi * df["day_of_week"] / 7
    )

    df["month_sin"] = np.sin(
        2 * np.pi * df["month"] / 12
    )

    df["month_cos"] = np.cos(
        2 * np.pi * df["month"] / 12
    )

    return df


def _add_segment_id(g: pd.DataFrame) -> pd.Series:
    """Create contiguous-series IDs.

    A large timestamp gap starts a new segment.

    This prevents historical features from before an outage/data gap from
    appearing after the gap.
    """

    gap_threshold = pd.Timedelta(
        minutes=NOMINAL_SAMPLING_MINUTES
        * GAP_MULTIPLE_THRESHOLD
    )

    starts_new_segment = (
        g["timestamp"].diff() > gap_threshold
    )

    return starts_new_segment.fillna(False).cumsum()


def add_historical_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Add past-only lag/rolling features without crossing large gaps."""

    df = (
        df
        .sort_values(["equipment_id", "timestamp"])
        .copy()
    )

    out_frames = []

    for _, g in df.groupby(
        "equipment_id",
        sort=False,
    ):
        g = g.copy()

        segment_id = _add_segment_id(g)

        for col in HISTORICAL_SOURCE_COLUMNS:

            safe_name = (
                col
                .split(" (")[0]
                .strip()
                .lower()
                .replace(" ", "_")
            )

            # ---------------------------------------------------------
            # LAGS
            # ---------------------------------------------------------

            for lag in LAG_STEPS:

                # Shift INSIDE the contiguous segment.
                # Therefore a lag can never reach across a large gap.
                g[f"lag_{lag}_{safe_name}"] = (
                    g.groupby(
                        segment_id,
                        sort=False,
                    )[col]
                    .shift(lag)
                )

            # ---------------------------------------------------------
            # ROLLING FEATURES
            # ---------------------------------------------------------

            for window in ROLLING_WINDOWS:

                # First shift by one so the current observation is never
                # included in its own historical feature.
                past = (
                    g.groupby(
                        segment_id,
                        sort=False,
                    )[col]
                    .shift(1)
                )

                min_periods = max(
                    2,
                    window // 4,
                )

                g[
                    f"roll_mean_{window}_{safe_name}"
                ] = (
                    past
                    .groupby(
                        segment_id,
                        sort=False,
                    )
                    .rolling(
                        window,
                        min_periods=min_periods,
                    )
                    .mean()
                    .reset_index(
                        level=0,
                        drop=True,
                    )
                )

                g[
                    f"roll_std_{window}_{safe_name}"
                ] = (
                    past
                    .groupby(
                        segment_id,
                        sort=False,
                    )
                    .rolling(
                        window,
                        min_periods=min_periods,
                    )
                    .std()
                    .reset_index(
                        level=0,
                        drop=True,
                    )
                )

        # -------------------------------------------------------------
        # ENERGY TREND
        # -------------------------------------------------------------

        past_target = (
            g.groupby(
                segment_id,
                sort=False,
            )[TARGET_COLUMN]
            .shift(1)
        )

        short_mean = (
            past_target
            .groupby(
                segment_id,
                sort=False,
            )
            .rolling(
                ROLLING_WINDOWS[0],
                min_periods=2,
            )
            .mean()
            .reset_index(
                level=0,
                drop=True,
            )
        )

        long_mean = (
            past_target
            .groupby(
                segment_id,
                sort=False,
            )
            .rolling(
                ROLLING_WINDOWS[-1],
                min_periods=4,
            )
            .mean()
            .reset_index(
                level=0,
                drop=True,
            )
        )

        g["energy_trend"] = (
            short_mean - long_mean
        )

        out_frames.append(g)

    return (
        pd.concat(
            out_frames,
            ignore_index=True,
        )
        .sort_values(
            ["equipment_id", "timestamp"]
        )
        .reset_index(drop=True)
    )


def build_feature_frame(
    df: pd.DataFrame,
    known_equipment: List[str] = None,
) -> Tuple[
    pd.DataFrame,
    List[str],
    List[str],
]:
    """Build model features.

    known_equipment fixes one-hot columns for inference against a previously
    trained model.
    """

    df = add_time_features(df)

    df = add_historical_features(df)

    time_features = [
        "hour_sin",
        "hour_cos",
        "dow_sin",
        "dow_cos",
        "month_sin",
        "month_cos",
        "is_weekend",
    ]

    op_env_features = (
        OPERATIONAL_COLUMNS
        + ENVIRONMENTAL_COLUMNS
    )

    historical_feature_cols = [
        c
        for c in df.columns
        if c.startswith("lag_")
        or c.startswith("roll_")
    ]

    historical_feature_cols += [
        "energy_trend"
    ]

    equipment_list = (
        known_equipment
        if known_equipment is not None
        else sorted(
            df["equipment_id"]
            .unique()
            .tolist()
        )
    )

    for eq in equipment_list:
        df[f"eq_{eq}"] = (
            df["equipment_id"] == eq
        ).astype(int)

    equipment_dummy_cols = [
        f"eq_{eq}"
        for eq in equipment_list
    ]

    feature_columns = (
        op_env_features
        + time_features
        + historical_feature_cols
        + equipment_dummy_cols
    )

    return (
        df,
        feature_columns,
        equipment_dummy_cols,
    )