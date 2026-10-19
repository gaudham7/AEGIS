"""
Data ingestion: schema validation, timestamp parsing, numeric validation,
equipment discovery, missing-value analysis and temporal-gap analysis.

This module is deliberately dataset-agnostic: it never assumes specific
equipment IDs, row counts, or date ranges. Everything is discovered from
whatever CSV is provided, as long as it conforms to the 11-column data
contract in config.py.
"""
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

from app.config import REQUIRED_COLUMNS, TARGET_COLUMN, NOMINAL_SAMPLING_MINUTES, GAP_MULTIPLE_THRESHOLD

NUMERIC_COLUMNS = [c for c in REQUIRED_COLUMNS if c not in ("timestamp", "equipment_id")]


class SchemaValidationError(Exception):
    pass


def validate_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """Check that all required columns are present. Extra columns are allowed
    and ignored (forward-compatible), but nothing required may be missing."""
    present = list(df.columns)
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in present]
    extra_cols = [c for c in present if c not in REQUIRED_COLUMNS]
    ok = len(missing_cols) == 0
    return {
        "ok": ok,
        "required_columns": REQUIRED_COLUMNS,
        "missing_columns": missing_cols,
        "extra_columns": extra_cols,
    }


def load_and_prepare(csv_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load a CSV, validate schema, parse timestamps/numerics, and return
    a cleaned dataframe (sorted) plus a report describing what was found.

    Raises SchemaValidationError if required columns are absent.
    """
    df = pd.read_csv(csv_path)
    schema_report = validate_schema(df)
    if not schema_report["ok"]:
        raise SchemaValidationError(
            f"Missing required columns: {schema_report['missing_columns']}"
        )

    df = df[REQUIRED_COLUMNS].copy()

    # --- timestamp parsing ---
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    n_bad_timestamps = int(df["timestamp"].isna().sum())
    df = df.dropna(subset=["timestamp"])

    # --- equipment id ---
    df["equipment_id"] = df["equipment_id"].astype(str).str.strip()
    df = df[df["equipment_id"] != ""]
    df = df[df["equipment_id"].str.lower() != "nan"]

    # --- numeric validation ---
    numeric_issue_counts = {}
    for col in NUMERIC_COLUMNS:
        before_na = df[col].isna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        after_na = df[col].isna().sum()
        numeric_issue_counts[col] = int(after_na - before_na)

    # drop exact duplicate (equipment_id, timestamp) rows, keep first
    dup_count = int(df.duplicated(subset=["equipment_id", "timestamp"]).sum())
    df = df.drop_duplicates(subset=["equipment_id", "timestamp"], keep="first")

    df = df.sort_values(["equipment_id", "timestamp"]).reset_index(drop=True)

    equipment_discovered = sorted(df["equipment_id"].unique().tolist())

    report = {
        "row_count": int(len(df)),
        "column_check": schema_report,
        "equipment_discovered": equipment_discovered,
        "bad_timestamp_rows_dropped": n_bad_timestamps,
        "duplicate_rows_dropped": dup_count,
        "numeric_coercion_new_nans": numeric_issue_counts,
        "time_range": {
            "start": df["timestamp"].min().isoformat() if len(df) else None,
            "end": df["timestamp"].max().isoformat() if len(df) else None,
        },
    }
    return df, report


def missing_value_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Per-column missing value counts, plus per-equipment breakdown."""
    total = len(df)
    per_column = {
        col: {
            "missing": int(df[col].isna().sum()),
            "pct": round(float(df[col].isna().mean()) * 100, 3) if total else 0.0,
        }
        for col in NUMERIC_COLUMNS
    }
    per_equipment = {}
    for eq, g in df.groupby("equipment_id"):
        per_equipment[eq] = {
            col: int(g[col].isna().sum()) for col in NUMERIC_COLUMNS
        }
    return {"per_column": per_column, "per_equipment": per_equipment, "total_rows": int(total)}


def temporal_gap_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Detect temporal gaps per equipment_id: consecutive timestamps whose
    difference exceeds GAP_MULTIPLE_THRESHOLD x the nominal sampling
    interval. These are reported (and later flagged, not filled), because a
    gap is a data-availability fact, not evidence of an anomaly."""
    nominal = pd.Timedelta(minutes=NOMINAL_SAMPLING_MINUTES)
    gap_threshold = nominal * GAP_MULTIPLE_THRESHOLD

    gaps_by_equipment: Dict[str, List[Dict[str, Any]]] = {}
    total_gaps = 0
    for eq, g in df.groupby("equipment_id"):
        g = g.sort_values("timestamp")
        diffs = g["timestamp"].diff()
        gap_mask = diffs > gap_threshold
        eq_gaps = []
        for idx in g.index[gap_mask]:
            pos = g.index.get_loc(idx)
            prev_ts = g["timestamp"].iloc[pos - 1]
            curr_ts = g["timestamp"].iloc[pos]
            eq_gaps.append({
                "gap_start": prev_ts.isoformat(),
                "gap_end": curr_ts.isoformat(),
                "gap_minutes": round((curr_ts - prev_ts).total_seconds() / 60, 1),
            })
        if eq_gaps:
            gaps_by_equipment[eq] = eq_gaps
            total_gaps += len(eq_gaps)

    return {
        "nominal_sampling_minutes": NOMINAL_SAMPLING_MINUTES,
        "gap_threshold_minutes": gap_threshold.total_seconds() / 60,
        "total_gaps": total_gaps,
        "gaps_by_equipment": gaps_by_equipment,
    }
