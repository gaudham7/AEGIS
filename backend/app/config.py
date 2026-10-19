"""
Central configuration for AEGIS backend.

Uses environment variables where practical. No secrets are hard-coded.
"""
import os
from pathlib import Path

# Project root is two levels above this file: backend/app/config.py -> AEGIS/
BASE_DIR = Path(os.environ.get("AEGIS_BASE_DIR", Path(__file__).resolve().parents[2]))

DATA_DIR = Path(os.environ.get("AEGIS_DATA_DIR", BASE_DIR / "data"))
MODELS_DIR = Path(os.environ.get("AEGIS_MODELS_DIR", BASE_DIR / "models"))
UPLOADS_DIR = DATA_DIR / "uploads"

for _dir in (DATA_DIR, MODELS_DIR, UPLOADS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Data contract (locked). New datasets must conform to these columns.
# ------------------------------------------------------------------

REQUIRED_COLUMNS = [
    "timestamp",
    "equipment_id",
    "Chilled Water Rate (L/sec)",
    "Cooling Water Temperature (C)",
    "Building Load (RT)",
    "Chiller Energy Consumption (kWh)",
    "Outside Temperature (F)",
    "Dew Point (F)",
    "Humidity (%)",
    "Wind Speed (mph)",
    "Pressure (in)",
]

TARGET_COLUMN = "Chiller Energy Consumption (kWh)"

OPERATIONAL_COLUMNS = [
    "Chilled Water Rate (L/sec)",
    "Cooling Water Temperature (C)",
    "Building Load (RT)",
]

ENVIRONMENTAL_COLUMNS = [
    "Outside Temperature (F)",
    "Dew Point (F)",
    "Humidity (%)",
    "Wind Speed (mph)",
    "Pressure (in)",
]

# Nominal sampling interval used for temporal-gap analysis (minutes).
NOMINAL_SAMPLING_MINUTES = 30

# A gap larger than this multiple of the nominal interval is treated as a
# "temporal gap" (data missing / equipment offline) rather than an ordinary
# missing value that can be safely interpolated.
GAP_MULTIPLE_THRESHOLD = 3  # i.e. > 90 minutes with a 30-minute nominal rate

# Small missing-value runs (in samples) that are considered safe to
# interpolate. Longer runs are left as NaN / flagged as gaps.
MAX_INTERPOLATION_RUN = 3

# Chronological split fractions (train / validation / test)
TRAIN_FRACTION = 0.7
VALIDATION_FRACTION = 0.15
# remainder is TEST_FRACTION

# Lag / rolling window sizes (in samples of the given equipment's own series)
LAG_STEPS = [1, 2, 3, 48]  # 30, 60, 90 min, ~1 day (48 * 30min)
ROLLING_WINDOWS = [4, 48]  # ~2 hours, ~1 day

# Anomaly scoring: modified z-score (MAD-based) threshold for flagging a
# single observation as "abnormal". 3.5 is the commonly used robust
# statistics convention (Iglewicz & Hoaglin).
ANOMALY_Z_THRESHOLD = 3.5

# Maximum gap (in samples) between two abnormal observations of the same
# equipment for them to still be grouped into the same abnormal period.
PERSISTENCE_MAX_GAP_SAMPLES = 1

RANDOM_STATE = 42
