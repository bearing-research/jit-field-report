"""Pipeline: join, groupby and built-in aggregation.

Joins trips to the taxi zone lookup twice (pickup and dropoff), then
aggregates by borough pair and hour with built-in reductions only. Expected to
be dominated by hash joins and Cython groupby kernels.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pipelines.common import clean_trips, read_trips, read_zones


def run(data_dir: Path) -> pd.DataFrame:
    trips = clean_trips(read_trips(data_dir))
    zones = read_zones(data_dir)[["LocationID", "Borough", "Zone"]]

    df = trips.merge(
        zones.rename(columns={"LocationID": "pu_location", "Borough": "pu_borough", "Zone": "pu_zone"}),
        on="pu_location",
        how="left",
    ).merge(
        zones.rename(columns={"LocationID": "do_location", "Borough": "do_borough", "Zone": "do_zone"}),
        on="do_location",
        how="left",
    )
    df["pickup_hour"] = df["pickup"].dt.hour

    agg = (
        df.groupby(["pu_borough", "do_borough", "pickup_hour"], dropna=False, sort=True)
        .agg(
            trips=("fare_amount", "size"),
            mean_fare=("fare_amount", "mean"),
            median_distance=("trip_distance", "median"),
            total_tips=("tip_amount", "sum"),
            mean_duration=("duration_min", "mean"),
            max_total=("total_amount", "max"),
        )
        .reset_index()
    )
    agg["share_of_pu_borough"] = agg["trips"] / agg.groupby("pu_borough", dropna=False)["trips"].transform("sum")

    zone_pairs = (
        df.groupby(["pu_borough", "pu_location", "do_location"], dropna=False).size().rename("pair_trips").reset_index()
    )
    pair_counts = (
        zone_pairs.groupby("pu_borough", dropna=False)
        .agg(distinct_zone_pairs=("pair_trips", "size"), busiest_pair_trips=("pair_trips", "max"))
        .reset_index()
    )
    return agg.merge(pair_counts, on="pu_borough", how="left")
