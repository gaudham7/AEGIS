from typing import Optional
from fastapi import APIRouter, HTTPException, Query
import pandas as pd

from app.models import database as db

router = APIRouter(prefix="/api", tags=["anomalies"])


def _require_periods(dataset_id: str):
    periods = db.load_json(dataset_id, "abnormal_periods")
    if periods is None:
        raise HTTPException(status_code=404, detail="No analysis found for this dataset. Train it first.")
    return periods


@router.get("/anomalies/{dataset_id}")
async def list_anomalies(dataset_id: str, equipment_id: Optional[str] = Query(None), severity: Optional[str] = Query(None)):
    periods = _require_periods(dataset_id)
    if equipment_id:
        periods = [p for p in periods if p["equipment_id"] == equipment_id]
    if severity:
        periods = [p for p in periods if p["severity_label"] == severity]
    return {"count": len(periods), "abnormal_periods": periods}


def _attach_observation_rows(dataset_id: str, period: dict, context_rows: int = 6) -> dict:
    """
    training.py/prediction.py intentionally strip 'observation_rows' from
    each period before saving (to keep the list payload lean), with the
    intent that row-level detail be reconstructed on demand for a single
    period. This rebuilds it from the separately-persisted 'scored_rows'
    artifact, filtered to this equipment.

    Timestamps are parsed with pandas rather than compared as raw strings:
    period start_time/end_time come from ml/persistence.py's .isoformat()
    ("2020-04-23T10:30:00"), while scored_rows timestamps come from
    training.py's .astype(str) on a datetime column ("2020-04-23
    10:30:00" — space, not "T"). Comparing those as strings is unreliable
    ("T" sorts after a space, so a "T"-formatted boundary can compare as
    "later" than an identical space-formatted instant) and was silently
    matching zero rows. Parsing both into actual timestamps sidesteps the
    formatting difference entirely.

    Also pads a few rows of context on either side of the abnormal window
    (default 6, i.e. ~3 hours either side at a 30-min interval) and marks
    each row with `in_period`, so the investigation chart can show "what
    did this look like right before/after" rather than only the abnormal
    rows in isolation.
    """
    scored_rows = db.load_json(dataset_id, "scored_rows") or []
    equipment_rows = [r for r in scored_rows if r.get("equipment_id") == period.get("equipment_id")]
    for r in equipment_rows:
        r["_ts"] = pd.Timestamp(r["timestamp"])
    equipment_rows.sort(key=lambda r: r["_ts"])

    start_ts = pd.Timestamp(period.get("start_time"))
    end_ts = pd.Timestamp(period.get("end_time"))

    in_window_idx = [i for i, r in enumerate(equipment_rows) if start_ts <= r["_ts"] <= end_ts]
    if not in_window_idx:
        return {**period, "observation_rows": []}

    lo = max(0, in_window_idx[0] - context_rows)
    hi = min(len(equipment_rows), in_window_idx[-1] + 1 + context_rows)

    rows = []
    for r in equipment_rows[lo:hi]:
        row = {k: v for k, v in r.items() if k != "_ts"}
        row["in_period"] = start_ts <= r["_ts"] <= end_ts
        rows.append(row)
    return {**period, "observation_rows": rows}


@router.get("/anomalies/{dataset_id}/{period_id}")
async def anomaly_detail(dataset_id: str, period_id: str):
    periods = _require_periods(dataset_id)
    for p in periods:
        if p["period_id"] == period_id:
            return _attach_observation_rows(dataset_id, p)
    raise HTTPException(status_code=404, detail="Abnormal period not found.")


@router.get("/timeline/{dataset_id}")
async def timeline(dataset_id: str, equipment_id: Optional[str] = Query(None)):
    periods = _require_periods(dataset_id)
    scored_rows = db.load_json(dataset_id, "scored_rows") or []
    if equipment_id:
        periods = [p for p in periods if p["equipment_id"] == equipment_id]
        scored_rows = [r for r in scored_rows if r["equipment_id"] == equipment_id]
    abnormal_observations = [r for r in scored_rows if r.get("is_abnormal")]
    timeline_periods = sorted(periods, key=lambda p: p["start_time"])
    abnormal_observations = sorted(abnormal_observations, key=lambda r: r["timestamp"])
    return {
        "abnormal_observations": abnormal_observations,
        "abnormal_periods": timeline_periods,
    }


@router.get("/overview/{dataset_id}")
async def overview(dataset_id: str):
    status = db.load_json(dataset_id, "status")
    if status is None or status.get("status") != "completed":
        raise HTTPException(status_code=404, detail="No completed analysis found for this dataset. Train it first.")
    periods = db.load_json(dataset_id, "abnormal_periods") or []
    scored_rows = db.load_json(dataset_id, "scored_rows") or []
    equipment_list = db.load_json(dataset_id, "equipment_list") or []

    energy_values = [r["actual_energy"] for r in scored_rows if r.get("actual_energy") is not None]
    avg_energy = round(sum(energy_values) / len(energy_values), 2) if energy_values else None

    recent_events = sorted(periods, key=lambda p: p["start_time"], reverse=True)[:5]
    priority_periods = sorted(periods, key=lambda p: p["severity_score"], reverse=True)[:5]

    return {
        "dataset_id": dataset_id,
        "equipment_discovered": equipment_list,
        "equipment_count": len(equipment_list),
        "monitoring_status": "active",
        "metrics": status.get("metrics"),
        "anomaly_summary": status.get("anomaly_summary"),
        "priority_abnormal_periods": priority_periods,
        "recent_events": recent_events,
        "energy_statistics": {
            "avg_actual_energy_kwh": avg_energy,
            "n_scored_observations": len(scored_rows),
        },
    }