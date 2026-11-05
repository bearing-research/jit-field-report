"""Pipeline: read, clean, transform and filter.

Input: one month of NYC TLC yellow taxi trips (about 3 million rows).
Mostly native kernels with a real Python layer: column renames, boolean
filtering, datetime accessors, dictionary mapping, string concatenation and
categorical conversion.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from pipelines.common import PAYMENT_TYPES, clean_trips, read_trips


def run(data_dir: Path) -> pd.DataFrame:
    df = clean_trips(read_trips(data_dir))

    df["speed_mph"] = (df["trip_distance"] / (df["duration_min"] / 60.0)).clip(upper=80.0)
    df["pickup_hour"] = df["pickup"].dt.hour.astype("int8")
    df["pickup_weekday"] = df["pickup"].dt.day_name()
    df["payment"] = df["payment_type"].map(PAYMENT_TYPES).fillna("other").astype("category")
    df["store_and_fwd"] = df["store_and_fwd_flag"].eq("Y")
    df["vendor_id"] = df["vendor_id"].astype("category")
    df["route"] = df["pu_location"].astype(str) + "-" + df["do_location"].astype(str)
    df["tip_pct"] = np.where(df["fare_amount"] > 0, df["tip_amount"] / df["fare_amount"], 0.0)

    out = df.loc[
        df["speed_mph"].between(1.0, 80.0) & df["total_amount"].between(0.0, 500.0),
        [
            "vendor_id",
            "pickup",
            "pickup_hour",
            "pickup_weekday",
            "pu_location",
            "do_location",
            "route",
            "passenger_count",
            "trip_distance",
            "duration_min",
            "speed_mph",
            "payment",
            "store_and_fwd",
            "fare_amount",
            "tip_pct",
            "total_amount",
        ],
    ]
    return out.sort_values(["pickup", "pu_location", "do_location"], kind="stable").reset_index(drop=True)
