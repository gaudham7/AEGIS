from fastapi import APIRouter, HTTPException

from app.models import database as db

router = APIRouter(prefix="/api/equipment", tags=["equipment"])


@router.get("/{dataset_id}")
async def list_equipment(dataset_id: str):
    equipment_list = db.load_json(dataset_id, "equipment_list")
    if equipment_list is None:
        raise HTTPException(status_code=404, detail="No trained model for this dataset yet.")
    periods = db.load_json(dataset_id, "abnormal_periods") or []
    scored_rows = db.load_json(dataset_id, "scored_rows") or []

    summaries = []
    for eq in equipment_list:
        eq_periods = [p for p in periods if p["equipment_id"] == eq]
        eq_rows = [r for r in scored_rows if r["equipment_id"] == eq]
        n_abnormal = sum(1 for r in eq_rows if r.get("is_abnormal"))
        avg_energy = round(sum(r["actual_energy"] for r in eq_rows) / len(eq_rows), 2) if eq_rows else None
        summaries.append({
            "equipment_id": eq,
            "n_scored_observations": len(eq_rows),
            "n_abnormal_observations": n_abnormal,
            "n_abnormal_periods": len(eq_periods),
            "high_priority_periods": len([p for p in eq_periods if p["severity_label"] == "high"]),
            "avg_actual_energy_kwh": avg_energy,
            "status": "attention_needed" if any(p["severity_label"] == "high" for p in eq_periods) else (
                "monitor" if eq_periods else "normal"
            ),
        })
    return {"equipment": summaries}


@router.get("/{dataset_id}/{equipment_id}")
async def equipment_detail(dataset_id: str, equipment_id: str):
    scored_rows = db.load_json(dataset_id, "scored_rows")
    if scored_rows is None:
        raise HTTPException(status_code=404, detail="No trained model for this dataset yet.")
    periods = db.load_json(dataset_id, "abnormal_periods") or []

    eq_rows = sorted(
        [r for r in scored_rows if r["equipment_id"] == equipment_id],
        key=lambda r: r["timestamp"],
    )
    if not eq_rows:
        raise HTTPException(status_code=404, detail="Equipment not found in scored results.")
    eq_periods = [p for p in periods if p["equipment_id"] == equipment_id]

    return {
        "equipment_id": equipment_id,
        "energy_history": eq_rows,
        "abnormal_periods": eq_periods,
        "n_observations": len(eq_rows),
        "n_abnormal_observations": sum(1 for r in eq_rows if r.get("is_abnormal")),
    }
