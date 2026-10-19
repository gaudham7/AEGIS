"""
XGBoost Regressor: the PRIMARY model.

This model is NOT a direct anomaly classifier. Its job is to learn
"expected energy consumption" for a given equipment unit under given
operating and environmental conditions and time context. The residual
(actual - expected) is what downstream anomaly detection is built on.
"""
from typing import Optional
import numpy as np
import pandas as pd
import xgboost as xgb

from app.config import RANDOM_STATE


def train_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: Optional[pd.DataFrame] = None,
    y_val: Optional[pd.Series] = None,
) -> xgb.XGBRegressor:
    model = xgb.XGBRegressor(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        early_stopping_rounds=30 if X_val is not None else None,
        eval_metric="mae",
    )
    eval_set = [(X_val, y_val)] if X_val is not None and y_val is not None else None
    model.fit(
        X_train, y_train,
        eval_set=eval_set,
        verbose=False,
    )
    return model


def predict_xgboost(model: xgb.XGBRegressor, X: pd.DataFrame) -> np.ndarray:
    return model.predict(X)
