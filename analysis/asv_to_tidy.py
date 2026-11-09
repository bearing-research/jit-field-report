"""Convert asv result JSON files into the tidy CSV that `paired.py` reads.

asv writes one JSON per (machine, commit, environment) and OVERWRITES it on
the next invocation with the same three keys. Two things follow for the
paired design:

1. Run the two arms under different machine labels, so they do not share a
   file (an `existing:` environment ignores asv's env matrix):

       PYTHON_JIT=0 asv run --machine c7i-metal-jit-off -E existing:$PY ...
       PYTHON_JIT=1 asv run --machine c7i-metal-jit-on  -E existing:$PY ...

2. After each paired invocation, move the two result files out of `.asv/`
   into `results/<run>/asv/run-NN/off.json` and `.../on.json`, or the next
   invocation overwrites them. Each `run-NN` directory is one independent
   paired run.

The converter expands parameterised benchmarks into one row per parameter
combination, keeps `time_*` and `peakmem_*` benchmarks by default, and
writes failed or missing results to a separate failures CSV so they are
reported rather than lost.

    python analysis/asv_to_tidy.py results/<run>/asv --out results/<run>/tidy.csv
    python analysis/asv_to_tidy.py --pair 1 off.json on.json --pair 2 off2.json on2.json \
        --out tidy.csv

Output columns: benchmark,params,run,arm,time_s,kind,started_at,repeat,number
(`paired.py` uses the first five; the rest are provenance).
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from pathlib import Path

DEFAULT_KINDS = ("time", "peakmem")


def _kind(benchmark: str) -> str:
    leaf = benchmark.rsplit(".", 1)[-1]
    for prefix in ("timeraw", "time", "peakmem", "mem", "track"):
        if leaf.startswith(prefix + "_"):
            return prefix
    return "other"


def _params_label(combo: tuple[str, ...]) -> str:
    """asv gives parameter values as strings already repr'd; keep them as a tuple string."""
    return repr(tuple(combo))


def rows_from_file(path: Path, run: str, arm: str, kinds: tuple[str, ...]):
    """Yield (ok_rows, failure_rows) for one asv result file."""
    data = json.loads(path.read_text())
    columns = data["result_columns"]
    ok, failed = [], []
    for benchmark, values in data["results"].items():
        kind = _kind(benchmark)
        if kind not in kinds:
            continue
        rec = dict(zip(columns, values))
        result = rec.get("result")
        params = rec.get("params") or []
        combos = list(itertools.product(*params)) if params else [()]
        if result is None:
            for combo in combos:
                failed.append({"benchmark": benchmark, "params": _params_label(combo),
                               "run": run, "arm": arm, "reason": "no result (benchmark failed or skipped)"})
            continue
        if len(result) != len(combos):
            raise ValueError(
                f"{path}: {benchmark} has {len(result)} results for {len(combos)} parameter combinations"
            )
        repeats = rec.get("stats_repeat") or [None] * len(combos)
        numbers = rec.get("stats_number") or [None] * len(combos)
        for i, combo in enumerate(combos):
            value = result[i]
            label = _params_label(combo)
            if value is None or (isinstance(value, float) and value != value):
                failed.append({"benchmark": benchmark, "params": label, "run": run,
                               "arm": arm, "reason": "null result for this parameter combination"})
                continue
            ok.append({
                "benchmark": benchmark, "params": label, "run": run, "arm": arm,
                "time_s": value, "kind": kind, "started_at": rec.get("started_at"),
                "repeat": repeats[i], "number": numbers[i],
            })
    return ok, failed


def discover_pairs(asv_dir: Path) -> list[tuple[str, Path, Path]]:
    pairs = []
    for run_dir in sorted(p for p in asv_dir.iterdir() if p.is_dir() and p.name.startswith("run-")):
        off, on = run_dir / "off.json", run_dir / "on.json"
        if not (off.exists() and on.exists()):
            print(f"warning: {run_dir} lacks off.json or on.json; skipped", file=sys.stderr)
            continue
        pairs.append((run_dir.name.removeprefix("run-"), off, on))
    return pairs


def convert(pairs: list[tuple[str, Path, Path]], kinds: tuple[str, ...]):
    ok_rows, fail_rows = [], []
    for run, off, on in pairs:
        for arm, path in (("off", off), ("on", on)):
            ok, failed = rows_from_file(path, run, arm, kinds)
            ok_rows.extend(ok)
            fail_rows.extend(failed)
    return ok_rows, fail_rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("asv_dir", nargs="?", type=Path, help="directory of run-NN/{off,on}.json")
    parser.add_argument("--pair", nargs=3, action="append", metavar=("RUN", "OFF_JSON", "ON_JSON"),
                        default=[], help="one independent paired run")
    parser.add_argument("--kinds", default=",".join(DEFAULT_KINDS),
                        help="benchmark kinds to keep (time,timeraw,peakmem,mem,track)")
    parser.add_argument("--out", type=Path, required=True, help="tidy CSV path")
    parser.add_argument("--failures", type=Path, help="failures CSV (default: <out>-failures.csv)")
    args = parser.parse_args(argv)

    pairs = [(r, Path(o), Path(n)) for r, o, n in args.pair]
    if args.asv_dir:
        pairs.extend(discover_pairs(args.asv_dir))
    if not pairs:
        parser.error("no paired runs given")

    kinds = tuple(k.strip() for k in args.kinds.split(","))
    ok_rows, fail_rows = convert(pairs, kinds)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["benchmark", "params", "run", "arm", "time_s",
                                           "kind", "started_at", "repeat", "number"])
        w.writeheader()
        w.writerows(ok_rows)
    failures = args.failures or args.out.with_name(args.out.stem + "-failures.csv")
    with failures.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["benchmark", "params", "run", "arm", "reason"])
        w.writeheader()
        w.writerows(fail_rows)

    runs = sorted({r["run"] for r in ok_rows})
    print(f"{len(ok_rows)} rows from {len(pairs)} paired run(s) {runs}; "
          f"{len(fail_rows)} failed or missing results -> {failures.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
