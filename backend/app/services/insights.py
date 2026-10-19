"""
Turn a detected abnormal period + its model-associated contributing
factors + operating context into a human-readable investigation insight.

Language rules (enforced here, per project spec):
 - Never assert a specific physical fault (compressor, refrigerant leak,
   bearing, mechanical failure, etc.) - the dataset carries no fault labels.
 - Always frame contributing factors as "model-associated", not causal.
 - Always describe what is statistically unusual, how confident/persistent
   that finding is, and what should be investigated next - not a diagnosis.
"""
from typing import List, Dict, Any


def generate_period_insight(period: Dict[str, Any], contributing_factors: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    eq = period["equipment_id"]
    direction = "higher than expected" if period["avg_residual"] > 0 else "lower than expected"
    severity = period["severity_label"]

    evidence_lines = [
        f"Equipment {eq} consumed energy that was, on average, "
        f"{abs(period['avg_residual']):.1f} kWh {direction} for the operating and "
        f"environmental conditions observed at the time.",
        f"This deviation was flagged across {period['n_abnormal_observations']} consecutive "
        f"observation(s) spanning approximately {period['duration_minutes']:.0f} minutes, "
        f"with a peak unusualness score of {period['max_unusualness']:.2f} "
        f"(robust z-score; values beyond ~3.5 are considered statistically unusual).",
    ]
    if period["recurrence_count_for_equipment"] > 1:
        evidence_lines.append(
            f"Equipment {eq} has {period['recurrence_count_for_equipment']} separate abnormal "
            "periods on record, suggesting this may be a recurring pattern rather than an isolated event."
        )

    if contributing_factors:
        factor_desc = "; ".join(
            f"{f['feature']} ({f['direction']})" for f in contributing_factors[:3]
        )
        evidence_lines.append(f"Model-associated contributing factors: {factor_desc}.")

    recommendation = _recommendation_for(severity, period)

    return {
        "summary": (
            f"{severity.upper()} priority: abnormal energy behaviour detected for {eq} "
            f"between {period['start_time']} and {period['end_time']}."
        ),
        "evidence": evidence_lines,
        "contributing_factors": contributing_factors or [],
        "recommended_investigation": recommendation,
        "disclaimer": (
            "This finding describes statistically unusual energy behaviour relative to the "
            "model's learned expectations under similar conditions. It does not identify a "
            "specific physical fault; the dataset contains no fault labels to confirm root cause."
        ),
    }


def _recommendation_for(severity: str, period: Dict[str, Any]) -> List[str]:
    base = [
        f"Review operating logs for {period['equipment_id']} during the flagged window "
        f"({period['start_time']} to {period['end_time']}).",
        "Compare actual vs. expected energy consumption against maintenance and setpoint records.",
    ]
    if severity == "high":
        base.append("Prioritize a physical inspection given the magnitude and/or persistence of this deviation.")
    if period["recurrence_count_for_equipment"] > 1:
        base.append("Check whether previous abnormal periods for this equipment share similar contributing factors.")
    base.append("Confirm the deviation is not explained by an unmodeled operational change (e.g. setpoint change, scheduled maintenance).")
    return base
