from typing import Optional
from fastapi import APIRouter, HTTPException, Query

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


def _attach_observation_rows(dataset_id: str, period: dict) -> dict:
    """
    training.py/prediction.py intentionally strip 'observation_rows' from
    each period before saving (to keep the list payload lean), with the
    intent that row-level detail be reconstructed on demand for a single
    period. This rebuilds it from the separately-persisted 'scored_rows'
    artifact, filtered to this period's equipment and time window.
    """
    scored_rows = db.load_json(dataset_id, "scored_rows") or []
    rows = [
        r for r in scored_rows
        if r.get("equipment_id") == period.get("equipment_id")
        and period.get("start_time") <= r.get("timestamp") <= period.get("end_time")
    ]
    rows.sort(key=lambda r: r.get("timestamp", ""))
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