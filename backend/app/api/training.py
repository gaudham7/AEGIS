from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.models import database as db
from app.models.schemas import TrainStatus
from app.services.training import run_training_pipeline, get_status

router = APIRouter(prefix="/api/train", tags=["training"])


def _run_training_safely(dataset_id: str) -> None:
    """
    Runs in the background. Any failure is written to status.json so the
    frontend's polling loop sees it, since there's no request/response
    cycle left to raise an HTTPException into by this point.
    """
    try:
        run_training_pipeline(dataset_id)
    except ValueError as e:
        db.save_json(dataset_id, "status", {
            "dataset_id": dataset_id, "status": "failed", "stage": "failed", "message": str(e),
        })
    except Exception as e:
        db.save_json(dataset_id, "status", {
            "dataset_id": dataset_id, "status": "failed", "stage": "failed",
            "message": f"Training failed: {e}",
        })


@router.post("/{dataset_id}", response_model=TrainStatus)
async def train_dataset(dataset_id: str, background_tasks: BackgroundTasks):
    if not db.upload_path(dataset_id).exists():
        raise HTTPException(status_code=404, detail="Dataset not found. Upload it first.")

    existing = db.load_json(dataset_id, "status")
    if existing and existing.get("status") == "running":
        # Already in progress (e.g. auto-train fired twice) — just return
        # the current status instead of starting a second run.
        return existing

    status = {
        "dataset_id": dataset_id,
        "status": "running",
        "stage": "queued",
        "message": "Training queued.",
    }
    db.save_json(dataset_id, "status", status)
    background_tasks.add_task(_run_training_safely, dataset_id)
    return status


@router.get("/status/{dataset_id}", response_model=TrainStatus)
async def training_status(dataset_id: str):
    return get_status(dataset_id)
