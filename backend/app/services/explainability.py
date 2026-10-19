"""
SHAP-based explainability for the XGBoost expected-energy model.

We expose "model-associated contributing factors" - the features that most
influenced the model's expected-energy prediction for a given
observation/period - rather than claiming any physical root cause. The
dataset carries no fault labels, so no specific physical fault (compressor,
refrigerant, bearing, etc.) is ever asserted; only statistical evidence
from the model's own behaviour.
"""
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

try:
    import shap
    SHAP_AVAILABLE = True
except Exception:  # pragma: no cover - defensive import guard
    SHAP_AVAILABLE = False


_EXPLAINER_CACHE: Dict[str, Any] = {}


def build_explainer(model, dataset_id: str):
    if not SHAP_AVAILABLE:
        return None
    if dataset_id in _EXPLAINER_CACHE:
        return _EXPLAINER_CACHE[dataset_id]
    try:
        explainer = shap.TreeExplainer(model)
        _EXPLAINER_CACHE[dataset_id] = explainer
        return explainer
    except Exception:
        return None


def top_contributing_factors(
    explainer, X_row: pd.DataFrame, feature_columns: List[str], top_n: int = 5
) -> Optional[List[Dict[str, Any]]]:
    """Return the top_n |SHAP value| features for a single-row dataframe,
    or None if SHAP is unavailable / fails (the caller degrades gracefully)."""
    if explainer is None or not SHAP_AVAILABLE:
        return None
    try:
        shap_values = explainer.shap_values(X_row)
        values = np.asarray(shap_values)[0]
        pairs = list(zip(feature_columns, values))
        pairs.sort(key=lambda p: abs(p[1]), reverse=True)
        top = pairs[:top_n]
        return [
            {
                "feature": _humanize_feature_name(name),
                "shap_value": round(float(val), 4),
                "direction": "increased expected energy" if val > 0 else "decreased expected energy",
            }
            for name, val in top
        ]
    except Exception:
        return None


def _humanize_feature_name(name: str) -> str:
    if name.startswith("eq_"):
        return f"equipment identity ({name[3:]})"
    mapping = {
        "hour_sin": "time of day", "hour_cos": "time of day",
        "dow_sin": "day of week", "dow_cos": "day of week",
        "month_sin": "seasonal/month effect", "month_cos": "seasonal/month effect",
        "is_weekend": "weekend/weekday",
        "energy_trend": "recent energy trend",
    }
    if name in mapping:
        return mapping[name]
    if name.startswith("lag_"):
        return f"recent history: {name[4:].replace('_', ' ')}"
    if name.startswith("roll_mean_"):
        return f"recent average: {name[10:].replace('_', ' ')}"
    if name.startswith("roll_std_"):
        return f"recent variability: {name[9:].replace('_', ' ')}"
    return name
