"""
Generates a synthetic chiller time-series dataset conforming to the AEGIS
11-column data contract, purely for local testing of the pipeline. This is
NOT part of the shipped application logic and is not referenced anywhere
by equipment ID, row count, or date range (those are all discovered
dynamically by the app).
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)

start = pd.Timestamp("2025-01-01 00:00:00")
n_periods = 3000  # ~62.5 days at 30 min
timestamps = pd.date_range(start, periods=n_periods, freq="30min")

equipment_ids = ["UNIT-A7", "UNIT-B2", "UNIT-C9"]

rows = []
for eq_idx, eq in enumerate(equipment_ids):
    base_load = 200 + eq_idx * 40
    for i, ts in enumerate(timestamps):
        hour = ts.hour
        dow = ts.dayofweek
        # diurnal + weekly load pattern
        diurnal = 60 * np.sin((hour - 6) / 24 * 2 * np.pi) + 40
        weekly = -20 if dow >= 5 else 0
        outside_temp_f = 75 + 15 * np.sin((hour - 9) / 24 * 2 * np.pi) + rng.normal(0, 2)
        humidity = 55 + 10 * np.sin((hour - 14) / 24 * 2 * np.pi) + rng.normal(0, 3)
        dew_point_f = outside_temp_f - (100 - humidity) / 5
        wind_speed = max(0, rng.normal(8, 3))
        pressure = 29.9 + rng.normal(0, 0.05)

        building_load = max(30, base_load + diurnal + weekly + rng.normal(0, 8))
        chilled_water_rate = max(5, building_load * 0.06 + rng.normal(0, 1.5))
        cooling_water_temp = 24 + 0.05 * (outside_temp_f - 75) + rng.normal(0, 0.8)

        # true underlying relationship for expected energy
        expected_energy = (
            2.0 * building_load
            + 1.2 * chilled_water_rate
            + 0.8 * cooling_water_temp
            + 0.3 * (outside_temp_f - 70)
            + 5 * eq_idx
            + 30
        )
        noise = rng.normal(0, 6)
        energy = expected_energy + noise

        # inject a persistent contextual anomaly for one equipment/time window,
        # placed late in the series so it lands in the held-out validation/test
        # window (the only place anomaly scoring is applied).
        if eq == "UNIT-B2" and 2820 <= i <= 2860:
            energy += 90  # sustained excess consumption given the same operating conditions
        # inject an isolated spike (should NOT get "high" persistence severity)
        if eq == "UNIT-A7" and i == 2900:
            energy += 70

        rows.append({
            "timestamp": ts,
            "equipment_id": eq,
            "Chilled Water Rate (L/sec)": round(chilled_water_rate, 2),
            "Cooling Water Temperature (C)": round(cooling_water_temp, 2),
            "Building Load (RT)": round(building_load, 2),
            "Chiller Energy Consumption (kWh)": round(energy, 2),
            "Outside Temperature (F)": round(outside_temp_f, 2),
            "Dew Point (F)": round(dew_point_f, 2),
            "Humidity (%)": round(np.clip(humidity, 10, 100), 2),
            "Wind Speed (mph)": round(wind_speed, 2),
            "Pressure (in)": round(pressure, 2),
        })

df = pd.DataFrame(rows)

# inject some missing values (small runs) and one large temporal gap for one equipment
missing_idx = rng.choice(df.index, size=40, replace=False)
df.loc[missing_idx, "Humidity (%)"] = np.nan

df = df.sort_values(["equipment_id", "timestamp"]).reset_index(drop=True)
# simulate a large temporal gap by dropping a block of rows for UNIT-C9
drop_mask = (df["equipment_id"] == "UNIT-C9") & (df["timestamp"] >= pd.Timestamp("2025-01-20")) & (df["timestamp"] < pd.Timestamp("2025-01-21 12:00:00"))
df = df[~drop_mask].reset_index(drop=True)

df.to_csv("/home/claude/AEGIS/data/sample_dataset.csv", index=False)
print("rows:", len(df), "equipment:", sorted(df["equipment_id"].unique().tolist()))
