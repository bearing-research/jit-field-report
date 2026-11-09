"""Tests for asv_to_tidy against real asv 0.6.6 result files.

`testdata/asv/{off,on}.json` were produced in the sandbox on Nov 8, 2026 by
running a two-benchmark asv project (one plain, one with a 2x2 parameter
grid, plus a `track_` benchmark) under `--machine vm-jit-0` and
`--machine vm-jit-1` with an `existing:` environment on uv's CPython
3.15.0b4. They are a schema fixture; their timings mean nothing.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import asv_to_tidy as a2t  # noqa: E402
import paired  # noqa: E402

OFF = HERE / "testdata" / "asv" / "off.json"
ON = HERE / "testdata" / "asv" / "on.json"


def test_expands_parameters_and_filters_kinds():
    ok, failed = a2t.rows_from_file(OFF, "1", "off", ("time",))
    names = {(r["benchmark"], r["params"]) for r in ok}
    assert ("jit_state.JitState.time_sum", "()") in names
    assert ("jit_state.Param.time_sum", "('10', \"'a'\")") in names
    assert len([r for r in ok if r["benchmark"] == "jit_state.Param.time_sum"]) == 4
    assert all(r["kind"] == "time" for r in ok)
    assert not any("track" in r["benchmark"] for r in ok)
    assert failed == []


def test_track_kept_only_when_asked():
    ok, _ = a2t.rows_from_file(ON, "1", "on", ("track",))
    assert [(r["benchmark"], r["time_s"]) for r in ok] == [("jit_state.JitState.track_jit_enabled", 1)]


def test_null_results_go_to_failures(tmp_path):
    data = json.loads(OFF.read_text())
    cols = data["result_columns"]
    entry = data["results"]["jit_state.Param.time_sum"]
    entry[cols.index("result")] = [None, 1e-6, 2e-6, 3e-6]
    data["results"]["jit_state.JitState.time_sum"][cols.index("result")] = None
    broken = tmp_path / "off.json"
    broken.write_text(json.dumps(data))
    ok, failed = a2t.rows_from_file(broken, "3", "off", ("time",))
    assert len(ok) == 3
    reasons = {(f["benchmark"], f["params"]) for f in failed}
    assert ("jit_state.JitState.time_sum", "()") in reasons
    assert ("jit_state.Param.time_sum", "('10', \"'a'\")") in reasons


def test_cli_discovery_and_paired_roundtrip(tmp_path):
    asv_dir = tmp_path / "asv"
    for run in ("01", "02", "03", "04", "05"):
        d = asv_dir / f"run-{run}"
        d.mkdir(parents=True)
        (d / "off.json").write_text(OFF.read_text())
        (d / "on.json").write_text(ON.read_text())
    (asv_dir / "run-06").mkdir()  # incomplete run: warned and skipped
    out = tmp_path / "tidy.csv"
    assert a2t.main([str(asv_dir), "--out", str(out)]) == 0
    rows = list(csv.DictReader(out.open()))
    assert len(rows) == 5 * 2 * 5  # runs x arms x (1 + 4) time results
    assert (tmp_path / "tidy-failures.csv").exists()

    import pandas as pd

    result = paired.paired_ratios(pd.read_csv(out, dtype={"params": str}), paired.load_thresholds())
    assert len(result) == 5
    assert set(result["n_runs"]) == {5}
    # identical runs -> zero spread -> every CI collapses; classes are not "insufficient"
    assert "insufficient" not in set(result["class"])


def test_mismatched_result_length_is_an_error(tmp_path):
    data = json.loads(OFF.read_text())
    cols = data["result_columns"]
    data["results"]["jit_state.Param.time_sum"][cols.index("result")] = [1e-6, 2e-6]
    broken = tmp_path / "off.json"
    broken.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="parameter combinations"):
        a2t.rows_from_file(broken, "1", "off", ("time",))
