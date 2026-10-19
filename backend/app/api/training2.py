from fastapi import APIRouter, HTTPException

from app.models import database as db
from app.models.schemas import TrainStatus
from app.services.training import run_training_pipeline, get_status

router = APIRouter(prefix="/api/train", tags=["training"])


@router.post("/{dataset_id}", response_model=TrainStatus)
async def train_dataset(dataset_id: str):
    if not db.upload_path(dataset_id).exists():
        raise HTTPException(status_code=404, detail="Dataset not found. Upload it first.")
    db.save_json(dataset_id, "status", {"dataset_id": dataset_id, "status": "running", "message": "Training in progress."})
    try:
        status = run_training_pipeline(dataset_id)
    except ValueError as e:
        status = {"dataset_id": dataset_id, "status": "failed", "message": str(e)}
        db.save_json(dataset_id, "status", status)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        status = {"dataset_id": dataset_id, "status": "failed", "message": f"Training failed: {e}"}
        db.save_json(dataset_id, "status", status)
        raise HTTPException(status_code=500, detail=f"Training failed: {e}")
    return status


@router.get("/status/{dataset_id}", response_model=TrainStatus)
async def training_status(dataset_id: str):
    return get_status(dataset_id)
