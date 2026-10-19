import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models import database as db
from app.models.schemas import UploadResponse
from app.services.ingestion import load_and_prepare, missing_value_analysis, temporal_gap_analysis, SchemaValidationError

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("", response_model=UploadResponse)
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    dataset_id = uuid.uuid4().hex[:12]
    dest = db.upload_path(dataset_id)
    contents = await file.read()
    with open(dest, "wb") as f:
        f.write(contents)

    try:
        df, ingestion_report = load_and_prepare(str(dest))
    except SchemaValidationError as e:
        db.delete_dataset(dataset_id)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        db.delete_dataset(dataset_id)
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    missing_report = missing_value_analysis(df)
    gap_report = temporal_gap_analysis(df)

    ready = ingestion_report["row_count"] >= 100 and len(ingestion_report["equipment_discovered"]) >= 1

    db.register_dataset(dataset_id, {
        "filename": file.filename,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "row_count": ingestion_report["row_count"],
        "equipment": ingestion_report["equipment_discovered"],
    })
    db.save_json(dataset_id, "upload_report", {
        "ingestion_report": ingestion_report,
        "missing_report": missing_report,
        "gap_report": gap_report,
    })

    return UploadResponse(
        dataset_id=dataset_id,
        filename=file.filename,
        row_count=ingestion_report["row_count"],
        column_check=ingestion_report["column_check"],
        equipment_discovered=ingestion_report["equipment_discovered"],
        time_range=ingestion_report["time_range"],
        missing_values=missing_report,
        temporal_gaps=gap_report,
        ready_for_training=ready,
        message="Dataset validated successfully." if ready else "Dataset uploaded but may be too small/incomplete for reliable training.",
    )


@router.get("/list")
async def list_datasets():
    return db.get_registry()
