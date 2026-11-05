"""Paired JIT-on / JIT-off ratios with confidence intervals and classification.

Input is a tidy CSV, one row per (benchmark, params, run, arm):

    benchmark,params,run,arm,time_s
    groupby.Apply.time_scalar_function_single_col,"(4,)",1,off,0.01234
    groupby.Apply.time_scalar_function_single_col,"(4,)",1,on,0.01180

`run` identifies one independent invocation pair: the off and on arms with the
same `run` were measured back to back on the same host. `time_s` is that
invocation's summary time (for asv, the reported value for the benchmark).
Repeats inside one invocation are not independent and must not appear as
separate runs.

The interval is a t-interval on the mean log ratio, reported as a geometric
mean ratio. Classification uses analysis/thresholds.toml:

    improved      whole CI below improved_below
    regressed     whole CI above regressed_above
    no_effect     whole CI inside [improved_below, regressed_above]
    inconclusive  anything else
    insufficient  fewer paired runs than min_independent_runs

  python analysis/paired.py results/<run>/tidy.csv --out results/<run>/paired.csv
"""

from __future__ import annotations

import argparse
import math
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

THRESHOLDS = Path(__file__).with_name("thresholds.toml")


def load_thresholds(path: Path = THRESHOLDS) -> dict:
    t = tomllib.loads(path.read_text())
    if not t["improved_below"] < 1.0 < t["regressed_above"]:
        raise ValueError("thresholds must satisfy improved_below < 1 < regressed_above")
    return t


def classify(lo: float, hi: float, n: int, t: dict) -> str:
    if n < t["min_independent_runs"]:
        return "insufficient"
    if hi < t["improved_below"]:
        return "improved"
    if lo > t["regressed_above"]:
        return "regressed"
    if lo >= t["improved_below"] and hi <= t["regressed_above"]:
        return "no_effect"
    return "inconclusive"


def paired_ratios(tidy: pd.DataFrame, t: dict) -> pd.DataFrame:
    required = {"benchmark", "params", "run", "arm", "time_s"}
    missing = required - set(tidy.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    if not set(tidy["arm"].unique()) <= {"off", "on"}:
        raise ValueError("arm must be 'off' or 'on'")
    if (tidy["time_s"] <= 0).any():
        raise ValueError("time_s must be positive")

    wide = tidy.pivot_table(
        index=["benchmark", "params", "run"], columns="arm", values="time_s", aggfunc="first"
    )
    unpaired = wide[wide.isna().any(axis=1)]
    wide = wide.dropna()
    log_ratio = np.log(wide["on"] / wide["off"])

    rows = []
    for (bench, params), lr in log_ratio.groupby(level=["benchmark", "params"]):
        values = lr.to_numpy()
        n = len(values)
        mean = float(values.mean())
        if n >= 2:
            sem = float(values.std(ddof=1) / math.sqrt(n))
            half = float(stats.t.ppf(0.5 + t["confidence_level"] / 2, df=n - 1)) * sem
        else:
            half = math.inf
        lo, hi = math.exp(mean - half), math.exp(mean + half)
        rows.append(
            {
                "benchmark": bench,
                "params": params,
                "n_runs": n,
                "ratio": math.exp(mean),
                "ci_low": lo,
                "ci_high": hi,
                "class": classify(lo, hi, n, t),
            }
        )
    out = pd.DataFrame(rows)
    if len(unpaired):
        dropped = unpaired.reset_index()[["benchmark", "params", "run"]]
        print(f"warning: {len(dropped)} unpaired runs dropped", file=sys.stderr)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tidy_csv", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path, default=THRESHOLDS)
    args = parser.parse_args()

    t = load_thresholds(args.thresholds)
    result = paired_ratios(pd.read_csv(args.tidy_csv, dtype={"params": str}), t)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.out, index=False)
    print(result["class"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
