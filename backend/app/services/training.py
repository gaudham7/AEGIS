"""
Orchestrates the full AEGIS training pipeline:

CSV -> ingestion/validation -> preprocessing -> feature engineering ->
chronological split -> baseline (LinearRegression) -> XGBoost ->
evaluation -> held-out residual calibration -> contextual anomaly
detection -> persistence grouping -> SHAP explanations -> insights ->
persisted artifacts.

This module contains no FastAPI-specific code so it can be tested/run
directly and reused for both the /training route and CLI-style scripts.
"""
from typing import Dict, Any
import joblib
import numpy as np
import pandas as pd

from app.config import (
    TARGET_COLUMN, TRAIN_FRACTION, VALIDATION_FRACTION, RANDOM_STATE,
)
from app.models import database as db
from app.services.ingestion import load_and_prepare, missing_value_analysis, temporal_gap_analysis
from app.services.preprocessing import handle_missing_values
from app.services.feature_engineering import build_feature_frame
from app.ml.baseline import train_baseline, predict_baseline
from app.ml.xgboost_model import train_xgboost, predict_xgboost
from app.ml.evaluation import regression_metrics
from app.ml.residual_analysis import calibrate_residual_stats
from app.services.anomaly_detection import score_and_group
from app.services.explainability import build_explainer, top_contributing_factors, SHAP_AVAILABLE
from app.services.insights import generate_period_insight

# Ordered, human-readable stages surfaced to the frontend during training so
# the progress indicator reflects what the pipeline is actually doing right
# now, rather than an indeterminate spinner. Order here also defines the
# progress-bar fraction the frontend computes (stage index / total stages).
STAGE_LABELS: Dict[str, str] = {
    "queued": "Queued",
    "ingesting": "Validating and loading data",
    "preprocessing": "Handling missing values and gaps",
    "feature_engineering": "Engineering time-aware features",
    "training_baseline": "Training baseline model",
    "training_xgboost": "Training XGBoost model",
    "calibrating": "Calibrating expected-behaviour ranges",
    "detecting_anomalies": "Detecting abnormal periods",
    "generating_insights": "Generating explanations and insights",
    "finalizing": "Saving results",
    "completed": "Done",
}
STAGE_ORDER = list(STAGE_LABELS.keys())


def _update_stage(dataset_id: str, stage: str) -> None:
    db.save_json(dataset_id, "status", {
        "dataset_id": dataset_id,
        "status": "running",
        "stage": stage,
        "message": STAGE_LABELS.get(stage, stage),
    })


def _chronological_split(df: pd.DataFrame):
    """Global chronological split by timestamp quantiles. Using a single
    global time cutoff (rather than per-equipment cutoffs) guarantees the
    validation/test windows represent a later real-world period than
    training for every equipment unit simultaneously - avoiding any
    train/validation/test overlap in time."""
    df = df.sort_values("timestamp")
    unique_times = df["timestamp"].sort_values().unique()
    n = len(unique_times)
    train_cut = unique_times[int(n * TRAIN_FRACTION)]
    val_cut = unique_times[int(n * (TRAIN_FRACTION + VALIDATION_FRACTION))]

    train_df = df[df["timestamp"] <= train_cut]
    val_df = df[(df["timestamp"] > train_cut) & (df["timestamp"] <= val_cut)]
    test_df = df[df["timestamp"] > val_cut]
    return train_df, val_df, test_df, {
        "train_cutoff": str(train_cut), "validation_cutoff": str(val_cut),
    }


def run_training_pipeline(dataset_id: str) -> Dict[str, Any]:
    csv_path = db.upload_path(dataset_id)
    if not csv_path.exists():
        raise FileNotFoundError(f"No uploaded dataset found for id {dataset_id}")

    # 1. Ingestion / validation (re-run for a clean, canonical dataframe)
    _update_stage(dataset_id, "ingesting")
    df, ingestion_report = load_and_prepare(str(csv_path))
    missing_report = missing_value_analysis(df)
    gap_report = temporal_gap_analysis(df)

    # 2. Preprocessing (sensible missing-value handling; large gaps preserved)
    _update_stage(dataset_id, "preprocessing")
    df, preprocess_report = handle_missing_values(df)

    # 3. Feature engineering (past-only lag/rolling features, cyclic time, equipment one-hot)
    _update_stage(dataset_id, "feature_engineering")
    feat_df, feature_columns, equipment_dummy_cols = build_feature_frame(df)

    # rows need a full feature vector + a non-null target to be usable for train/eval
    model_df = feat_df.dropna(subset=feature_columns + [TARGET_COLUMN]).copy()
    if len(model_df) < 100:
        raise ValueError(
            f"Only {len(model_df)} rows have complete features after preprocessing; "
            "need at least 100 to train reliably. Provide more historical data."
        )

    # 4. Chronological split (no shuffling, no leakage across time)
    train_df, val_df, test_df, split_info = _chronological_split(model_df)
    if len(train_df) < 50 or len(val_df) < 10 or len(test_df) < 10:
        raise ValueError(
            "Not enough data across the chronological train/validation/test split "
            f"(train={len(train_df)}, val={len(val_df)}, test={len(test_df)}). "
            "Provide a longer historical dataset."
        )

    X_train, y_train = train_df[feature_columns], train_df[TARGET_COLUMN]
    X_val, y_val = val_df[feature_columns], val_df[TARGET_COLUMN]
    X_test, y_test = test_df[feature_columns], test_df[TARGET_COLUMN]

    # 5. Baseline
    _update_stage(dataset_id, "training_baseline")
    baseline_model = train_baseline(X_train, y_train)
    baseline_val_metrics = regression_metrics(y_val, predict_baseline(baseline_model, X_val))
    baseline_test_metrics = regression_metrics(y_test, predict_baseline(baseline_model, X_test))

    # 6. XGBoost (primary model)
    _update_stage(dataset_id, "training_xgboost")
    xgb_model = train_xgboost(X_train, y_train, X_val, y_val)
    xgb_val_pred = predict_xgboost(xgb_model, X_val)
    xgb_test_pred = predict_xgboost(xgb_model, X_test)
    xgb_val_metrics = regression_metrics(y_val, xgb_val_pred)
    xgb_test_metrics = regression_metrics(y_test, xgb_test_pred)

    # 7. Residual calibration - GENUINELY HELD-OUT (validation) predictions only
    _update_stage(dataset_id, "calibrating")
    val_residuals = y_val.values - xgb_val_pred
    residual_stats = calibrate_residual_stats(val_df["equipment_id"], pd.Series(val_residuals))

    # 8. Score anomalies across validation + test (both are held-out w.r.t. training)
    _update_stage(dataset_id, "detecting_anomalies")
    scoring_df = pd.concat([val_df, test_df]).sort_values(["equipment_id", "timestamp"])
    scoring_X = scoring_df[feature_columns]
    scoring_pred = predict_xgboost(xgb_model, scoring_X)
    scored = pd.DataFrame({
        "equipment_id": scoring_df["equipment_id"].values,
        "timestamp": scoring_df["timestamp"].values,
        "actual_energy": scoring_df[TARGET_COLUMN].values,
        "expected_energy": scoring_pred,
    })
    scored["residual"] = scored["actual_energy"] - scored["expected_energy"]
    # carry a few operating-context columns through for the investigation view
    for col in ["Building Load (RT)", "Chilled Water Rate (L/sec)", "Cooling Water Temperature (C)",
                "Outside Temperature (F)", "Humidity (%)"]:
        scored[col] = scoring_df[col].values

    anomaly_result = score_and_group(scored, residual_stats)
    scored_rows = anomaly_result["scored_rows"]
    abnormal_periods = anomaly_result["abnormal_periods"]

    # 9. SHAP explanations + insights per abnormal period (best-effort)
    _update_stage(dataset_id, "generating_insights")
    explainer = build_explainer(xgb_model, dataset_id)
    scoring_index_lookup = scoring_df.reset_index(drop=True)
    for period in abnormal_periods:
        rep_row = period["observation_rows"][0]
        mask = (
            (scoring_index_lookup["equipment_id"] == rep_row["equipment_id"]) &
            (scoring_index_lookup["timestamp"] == pd.Timestamp(rep_row["timestamp"]))
        )
        matched = scoring_index_lookup[mask]
        factors = None
        if len(matched) and explainer is not None:
            X_row = matched[feature_columns].iloc[[0]]
            factors = top_contributing_factors(explainer, X_row, feature_columns)
        period["insight"] = generate_period_insight(period, factors)
        period.pop("observation_rows", None)  # keep API payload lean; row detail available via anomalies endpoint

    equipment_list = sorted(df["equipment_id"].unique().tolist())

    # 10. Persist artifacts
    _update_stage(dataset_id, "finalizing")
    joblib.dump(xgb_model, db.artifact_path(dataset_id, "xgboost_model.joblib"))
    joblib.dump(baseline_model, db.artifact_path(dataset_id, "baseline_model.joblib"))

    db.save_json(dataset_id, "feature_columns", feature_columns)
    db.save_json(dataset_id, "equipment_list", equipment_list)
    db.save_json(dataset_id, "residual_stats", residual_stats)
    db.save_json(dataset_id, "split_info", split_info)
    db.save_json(dataset_id, "abnormal_periods", abnormal_periods)
    db.save_json(dataset_id, "scored_rows", scored_rows.assign(
        timestamp=scored_rows["timestamp"].astype(str)
    ).to_dict("records"))

    metrics = {
        "baseline": {"validation": baseline_val_metrics, "test": baseline_test_metrics},
        "xgboost": {"validation": xgb_val_metrics, "test": xgb_test_metrics},
        "improvement_over_baseline_test_mae_pct": round(
            100 * (baseline_test_metrics["mae"] - xgb_test_metrics["mae"]) / baseline_test_metrics["mae"], 2
        ) if baseline_test_metrics["mae"] else None,
        "shap_available": SHAP_AVAILABLE,
    }
    db.save_json(dataset_id, "metrics", metrics)

    ingestion_summary = {
        "ingestion_report": ingestion_report,
        "missing_report": missing_report,
        "gap_report": gap_report,
        "preprocess_report": preprocess_report,
        "rows_used_for_modeling": int(len(model_df)),
        "train_rows": int(len(train_df)), "validation_rows": int(len(val_df)), "test_rows": int(len(test_df)),
    }
    db.save_json(dataset_id, "ingestion_summary", ingestion_summary)

    status = {
        "dataset_id": dataset_id,
        "status": "completed",
        "stage": "completed",
        "message": "Training completed successfully.",
        "metrics": metrics,
        "equipment": equipment_list,
        "anomaly_summary": {
            "total_abnormal_periods": len(abnormal_periods),
            "high_priority": len([p for p in abnormal_periods if p["severity_label"] == "high"]),
            "medium_priority": len([p for p in abnormal_periods if p["severity_label"] == "medium"]),
            "low_priority": len([p for p in abnormal_periods if p["severity_label"] == "low"]),
            "total_abnormal_observations": int(scored_rows["is_abnormal"].sum()),
            "total_scored_observations": int(len(scored_rows)),
        },
    }
    db.save_json(dataset_id, "status", status)
    return status


def get_status(dataset_id: str) -> Dict[str, Any]:
    status = db.load_json(dataset_id, "status")
    if status is None:
        return {"dataset_id": dataset_id, "status": "not_started", "message": "Training has not been run for this dataset yet."}
    return status
