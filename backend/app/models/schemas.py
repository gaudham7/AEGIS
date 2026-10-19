"""Pydantic response/request models shared across API routes."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class UploadResponse(BaseModel):
    dataset_id: str
    filename: str
    row_count: int
    column_check: Dict[str, Any]
    equipment_discovered: List[str]
    time_range: Dict[str, Optional[str]]
    missing_values: Dict[str, Any]
    temporal_gaps: Dict[str, Any]
    ready_for_training: bool
    message: str


class TrainRequest(BaseModel):
    dataset_id: str


class TrainStatus(BaseModel):
    dataset_id: str
    status: str  # "not_started" | "running" | "completed" | "failed"
    stage: Optional[str] = None  # machine key, e.g. "training_xgboost" — see training.py STAGE_LABELS
    message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    equipment: Optional[List[str]] = None
    anomaly_summary: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
