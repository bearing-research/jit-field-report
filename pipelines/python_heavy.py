"""Pipeline: groupby with Python UDFs and feature engineering.

Python callables run inside pandas: groupby.apply with a per-zone UDF,
aggregations with lambdas, a row-wise apply on a fixed slice, and per-group
lag features. Expected to carry the largest share of Python-level time.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from pipelines.common import clean_trips, read_trips

ROW_APPLY_ROWS = 100_000


def zone_profile(g: pd.DataFrame) -> pd.Series:
    fares = np.sort(g["fare_amount"].to_numpy())
    k = len(fares) // 10
    trimmed = fares[k : len(fares) - k] if len(fares) > 2 * k else fares
    long_trips = 0
    for d in g["trip_distance"].to_numpy():
        if d > 10.0:
            long_trips += 1
    return pd.Series(
        {
            "trips": len(g),
            "trimmed_mean_fare": float(trimmed.mean()),
            "long_trip_share": long_trips / len(g),
            "fare_per_mile": float(g["fare_amount"].sum() / g["trip_distance"].sum()),
        }
    )


def fare_band(row: pd.Series) -> str:
    fare = row["fare_amount"]
    if row["trip_distance"] > 10.0:
        return "long"
    if fare < 10.0:
        return "low"
    if fare < 30.0:
        return "mid"
    return "high"


def run(data_dir: Path) -> pd.DataFrame:
    df = clean_trips(read_trips(data_dir))
    df = df.sort_values(["pickup", "pu_location", "do_location"], kind="stable").reset_index(drop=True)
    df["pickup_hour"] = df["pickup"].dt.hour

    profile = df.groupby("pu_location")[["fare_amount", "trip_distance"]].apply(zone_profile)

    lambdas = df.groupby("pu_location").agg(
        tip_iqr=("tip_amount", lambda s: s.quantile(0.75) - s.quantile(0.25)),
        busiest_hour=("pickup_hour", lambda s: int(s.value_counts().idxmax())),
    )

    head = df.iloc[:ROW_APPLY_ROWS]
    bands = (
        head.assign(band=head.apply(fare_band, axis=1))
        .groupby(["pu_location", "band"])
        .size()
        .unstack(fill_value=0)
        .add_prefix("band_")
    )

    hourly = df.groupby(["pu_location", "pickup_hour"]).size().rename("hourly_trips").reset_index()
    hourly["prev_hour_trips"] = hourly.groupby("pu_location")["hourly_trips"].shift(1)
    hourly["rolling_3h"] = hourly.groupby("pu_location")["hourly_trips"].transform(
        lambda s: s.rolling(3, min_periods=1).mean()
    )
    hour_features = hourly.groupby("pu_location").agg(
        peak_hourly_trips=("hourly_trips", "max"),
        max_rolling_3h=("rolling_3h", "max"),
        mean_hour_change=("prev_hour_trips", lambda s: float(np.nanmean(s.to_numpy())) if s.notna().any() else 0.0),
    )

    out = profile.join([lambdas, bands, hour_features], how="left")
    band_cols = [c for c in out.columns if c.startswith("band_")]
    out[band_cols] = out[band_cols].fillna(0).astype("int64")
    return out.sort_index().reset_index()
