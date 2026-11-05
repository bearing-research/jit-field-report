"""Synthetic checks for analysis/paired.py.  Run: python -m pytest analysis"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paired  # noqa: E402

T = {"improved_below": 0.98, "regressed_above": 1.02, "confidence_level": 0.95, "min_independent_runs": 5}


def make(true_ratio: float, n: int, noise: float, seed: int, bench: str = "b") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for run in range(n):
        base = 1.0 * np.exp(rng.normal(0, 0.05))  # host drift shared by both arms in a pair
        off = base * np.exp(rng.normal(0, noise))
        on = base * true_ratio * np.exp(rng.normal(0, noise))
        rows += [
            {"benchmark": bench, "params": "()", "run": run, "arm": "off", "time_s": off},
            {"benchmark": bench, "params": "()", "run": run, "arm": "on", "time_s": on},
        ]
    return pd.DataFrame(rows)


@pytest.mark.parametrize(
    "ratio,n,noise,expected",
    [
        (0.80, 10, 0.005, "improved"),
        (1.25, 10, 0.005, "regressed"),
        (1.00, 20, 0.002, "no_effect"),
        (0.98, 5, 0.05, "inconclusive"),
        (0.80, 3, 0.005, "insufficient"),
    ],
)
def test_classification(ratio, n, noise, expected):
    out = paired.paired_ratios(make(ratio, n, noise, seed=1), T)
    assert out.loc[0, "class"] == expected


def test_pairing_removes_shared_drift():
    # Large host drift but tiny within-pair noise: the paired design should still be precise.
    out = paired.paired_ratios(make(0.90, 6, 0.001, seed=2), T)
    assert out.loc[0, "ci_high"] - out.loc[0, "ci_low"] < 0.01
    assert abs(out.loc[0, "ratio"] - 0.90) < 0.005


def test_unpaired_run_dropped():
    df = make(0.9, 6, 0.001, seed=3)
    df = df.drop(df.index[-1])  # remove the last "on"
    out = paired.paired_ratios(df, T)
    assert out.loc[0, "n_runs"] == 5


def test_rejects_bad_input():
    df = make(0.9, 5, 0.001, seed=4)
    df.loc[0, "arm"] = "maybe"
    with pytest.raises(ValueError):
        paired.paired_ratios(df, T)


def test_thresholds_file_loads():
    t = paired.load_thresholds()
    assert t["improved_below"] < 1 < t["regressed_above"]
