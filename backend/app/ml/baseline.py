"""Linear Regression baseline.

Purpose: demonstrate that the primary XGBoost model provides meaningfully
better predictive performance than a simple linear model, before that
XGBoost model's residuals are trusted as the basis of anomaly detection.
"""
from typing import List, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


def train_baseline(X_train: pd.DataFrame, y_train: pd.Series) -> Pipeline:
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LinearRegression()),
    ])
    model.fit(X_train, y_train)
    return model


def predict_baseline(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    return model.predict(X)
