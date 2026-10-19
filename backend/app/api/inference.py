from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.prediction import score_new_observations, ModelNotTrainedError

router = APIRouter(prefix="/api/infer", tags=["inference"])


@router.post("/{dataset_id}")
async def infer(dataset_id: str, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")
    contents = await file.read()
    try:
        result = score_new_observations(dataset_id, contents)
    except ModelNotTrainedError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Inference failed: {e}")
    return result
