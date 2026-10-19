"""
Ties together residual scoring (app.ml.residual_analysis) and persistence
grouping (app.ml.persistence) into abnormal periods, ready for the API/
frontend layer. Kept separate from FastAPI routes and from the raw ML
model code so each concern stays independently testable.
"""
from typing import Dict, Any, List
import pandas as pd

from app.ml.residual_analysis import score_residuals
from app.ml.persistence import flag_abnormal_observations, group_abnormal_periods


def score_and_group(scored_df: pd.DataFrame, residual_stats: Dict[str, Any]) -> Dict[str, Any]:
    """`scored_df` must already contain: equipment_id, timestamp, residual,
    actual_energy, expected_energy. Adds unusualness_score, is_abnormal, and
    returns both the row-level dataframe and the grouped abnormal periods."""
    df = scored_df.copy()
    df["unusualness_score"] = score_residuals(df["equipment_id"], df["residual"], residual_stats)
    df = flag_abnormal_observations(df)
    periods = group_abnormal_periods(df)
    return {"scored_rows": df, "abnormal_periods": periods}
