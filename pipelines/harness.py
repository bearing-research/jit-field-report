"""Timing harness for the end-to-end pandas pipelines.

Each pipeline module exposes `run(data_dir: Path) -> pandas.DataFrame`.

Modes:
  fresh  one measured call in a new interpreter; the outer runner starts a new
         process per repetition, so JIT warmup is included in the time.
  warm   `--warmup` unmeasured calls, then `--repeat` measured calls in one process.

Every record carries the JIT state and a hash of the output, so the JIT-on and
JIT-off arms can be checked for identical results.

  python -m pipelines.harness data_prep --data-dir data/ --mode warm \
      --warmup 5 --repeat 20 --out results/run-001/data_prep-warm.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.check_jit import jit_state  # noqa: E402

PIPELINES = ("data_prep", "relational", "python_heavy")


def output_hash(df) -> str:
    import pandas as pd

    hashed = pd.util.hash_pandas_object(df, index=True).to_numpy()
    digest = hashlib.sha256(hashed.tobytes())
    digest.update(repr(list(df.columns)).encode())
    digest.update(repr(list(df.dtypes.astype(str))).encode())
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pipeline", choices=PIPELINES)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("fresh", "warm"), required=True)
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.mode == "fresh" and (args.warmup or args.repeat != 1):
        parser.error("fresh mode is one measured call per process")

    state = jit_state()
    module = importlib.import_module(f"pipelines.{args.pipeline}")

    for _ in range(args.warmup):
        module.run(args.data_dir)

    timings, hashes = [], set()
    for _ in range(args.repeat):
        start = time.perf_counter()
        result = module.run(args.data_dir)
        timings.append(time.perf_counter() - start)
        hashes.add(output_hash(result))

    record = {
        "pipeline": args.pipeline,
        "mode": args.mode,
        "warmup": args.warmup,
        "timings_s": timings,
        "output_hashes": sorted(hashes),
        # ru_maxrss is in KiB on Linux.
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "jit": state,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
