"""Shared loading for the pipelines. Inputs are pinned in data/MANIFEST.toml."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

TRIPS = "yellow_tripdata_2024-01.parquet"
ZONES = "taxi_zone_lookup.csv"

PAYMENT_TYPES = {
    0: "flex_fare",
    1: "credit_card",
    2: "cash",
    3: "no_charge",
    4: "dispute",
    5: "unknown",
    6: "voided",
}


def read_trips(data_dir: Path) -> pd.DataFrame:
    return pd.read_parquet(Path(data_dir) / TRIPS)


def read_zones(data_dir: Path) -> pd.DataFrame:
    return pd.read_csv(Path(data_dir) / ZONES)


def clean_trips(trips: pd.DataFrame) -> pd.DataFrame:
    """The cleaning step shared by every pipeline."""
    df = trips.rename(
        columns={
            "VendorID": "vendor_id",
            "tpep_pickup_datetime": "pickup",
            "tpep_dropoff_datetime": "dropoff",
            "RatecodeID": "ratecode_id",
            "PULocationID": "pu_location",
            "DOLocationID": "do_location",
            "Airport_fee": "airport_fee",
        }
    )
    df = df.dropna(subset=["passenger_count"])
    duration_min = (df["dropoff"] - df["pickup"]).dt.total_seconds() / 60.0
    keep = (
        (df["fare_amount"] >= 0)
        & (df["trip_distance"] > 0)
        & (duration_min > 0)
        & (df["pickup"] >= "2024-01-01")
        & (df["pickup"] < "2024-02-01")
    )
    df = df.loc[keep].copy()
    df["duration_min"] = duration_min[keep]
    return df
