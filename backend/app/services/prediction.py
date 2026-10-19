"""
Inference service - deliberately kept separate from training.

Given a dataset_id that has already been trained, this scores NEW
observation rows (conforming to the same 11-column data contract) using
the already-fitted XGBoost model and the residual statistics calibrated
during training, WITHOUT retraining anything.

Because lag/rolling features need real history, new rows are appended
(in memory only) to the tail of the original training CSV for the
relevant equipment before feature engineering, then only the newly
supplied rows are scored and returned.
"""
from typing import Dict, Any
import io
import joblib
import pandas as pd

from app.config import TARGET_COLUMN
from app.models import database as db
from app.services.ingestion import load_and_prepare
from app.services.feature_engineering import build_feature_frame
from app.ml.xgboost_model import predict_xgboost
from app.services.anomaly_detection import score_and_group
from app.services.explainability import build_explainer, top_contributing_factors
from app.services.insights import generate_period_insight


class ModelNotTrainedError(Exception):
    pass


def score_new_observations(dataset_id: str, new_csv_bytes: bytes) -> Dict[str, Any]:
    model_path = db.artifact_path(dataset_id, "xgboost_model.joblib")
    if not model_path.exists():
        raise ModelNotTrainedError(f"No trained model found for dataset {dataset_id}. Train first.")

    model = joblib.load(model_path)
    feature_columns = db.load_json(dataset_id, "feature_columns")
    residual_stats = db.load_json(dataset_id, "residual_stats")
    known_equipment = db.load_json(dataset_id, "equipment_list")

    # historical context for correct lag/rolling features
    history_df, _ = load_and_prepare(str(db.upload_path(dataset_id)))

    tmp_path = "/tmp/_aegis_new_obs.csv"
    with open(tmp_path, "wb") as f:
        f.write(new_csv_bytes)
    new_df, _ = load_and_prepare(tmp_path)

    unknown_equipment = sorted(set(new_df["equipment_id"]) - set(known_equipment))

    combined = pd.concat([history_df, new_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=["equipment_id", "timestamp"], keep="last")
    combined = combined.sort_values(["equipment_id", "timestamp"]).reset_index(drop=True)

    feat_df, _, _ = build_feature_frame(combined, known_equipment=known_equipment)

    new_keys = set(zip(new_df["equipment_id"], new_df["timestamp"]))
    mask = feat_df.apply(lambda r: (r["equipment_id"], r["timestamp"]) in new_keys, axis=1)
    infer_df = feat_df[mask].dropna(subset=feature_columns).copy()

    if infer_df.empty:
        return {
            "scored_observations": [],
            "abnormal_periods": [],
            "unknown_equipment": unknown_equipment,
            "message": "No new rows had sufficient feature history to score (need prior context for lag features).",
        }

    preds = predict_xgboost(model, infer_df[feature_columns])
    scored = pd.DataFrame({
        "equipment_id": infer_df["equipment_id"].values,
        "timestamp": infer_df["timestamp"].values,
        "actual_energy": infer_df[TARGET_COLUMN].values,
        "expected_energy": preds,
    })
    scored["residual"] = scored["actual_energy"] - scored["expected_energy"]
    for col in ["Building Load (RT)", "Chilled Water Rate (L/sec)", "Cooling Water Temperature (C)",
                "Outside Temperature (F)", "Humidity (%)"]:
        scored[col] = infer_df[col].values

    result = score_and_group(scored, residual_stats)
    scored_rows = result["scored_rows"]
    periods = result["abnormal_periods"]

    explainer = build_explainer(model, dataset_id)
    for period in periods:
        rep_row = period["observation_rows"][0]
        mask2 = (infer_df["equipment_id"] == rep_row["equipment_id"]) & (infer_df["timestamp"] == pd.Timestamp(rep_row["timestamp"]))
        matched = infer_df[mask2]
        factors = None
        if len(matched) and explainer is not None:
            factors = top_contributing_factors(explainer, matched[feature_columns].iloc[[0]], feature_columns)
        period["insight"] = generate_period_insight(period, factors)
        period.pop("observation_rows", None)

    return {
        "scored_observations": scored_rows.assign(timestamp=scored_rows["timestamp"].astype(str)).to_dict("records"),
        "abnormal_periods": periods,
        "unknown_equipment": unknown_equipment,
        "message": "Scored using existing trained model (no retraining performed).",
    }
