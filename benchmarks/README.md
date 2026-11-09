# pandas asv benchmarks

`selected.txt` is the pre-committed benchmark list. It is committed before any final run, and only benchmarks on it are reported, including null and inconclusive ones. Changes after the first final run go in its CHANGES block with a reason.

## Setup

1. Check out pandas at `[pandas] commit` from `pins.toml`; the asv suite in `asv_bench/` comes from the same commit.
2. Install that pandas into the pinned JIT build, with NumPy and pyarrow from the pinned wheels.
3. Point asv at that interpreter with an `existing:` environment, since the repo default is a rattler environment.
4. Run each arm with `PYTHON_JIT=0` or `PYTHON_JIT=1` under its own machine label, and log `scripts/check_jit.py` output from inside a benchmark process:

   ```
   PYTHON_JIT=0 asv run --machine c7i-metal-jit-off -E existing:$PY --set-commit-hash $PANDAS_SHA -b "$(paste -sd'|' <(grep -v '^#' selected.txt | awk '{print $1}'))"
   PYTHON_JIT=1 asv run --machine c7i-metal-jit-on  -E existing:$PY --set-commit-hash $PANDAS_SHA -b ...
   mkdir -p results/<run>/asv/run-01 && mv .asv/results/c7i-metal-jit-off/*.json results/<run>/asv/run-01/off.json \
                                    && mv .asv/results/c7i-metal-jit-on/*.json  results/<run>/asv/run-01/on.json
   ```

   The move is not optional: asv overwrites the result file for the same (machine, commit, environment) on the next invocation, and an `existing:` environment ignores asv's env matrix, so machine labels are what keep the arms apart (see `analysis/README.md`).

Week 1 checks, before any final run:

- [x] `PYTHON_JIT` reaches asv's benchmark subprocesses: confirmed Nov 8 in the sandbox (asv 0.6.6, `existing:` env on uv's 3.15.0b4): `jit_enabled` flips False/True inside the benchmark process and a `track_` benchmark returns 0/1. Re-run `check_jit` from inside one pandas benchmark on the study build as a formality; the two-builds fallback is not expected to be needed.
- [ ] Wall time of one paired run of the selected set on the bare-metal host.
- [ ] Run-to-run spread, to set the number of independent paired runs.

## Statistics

- Independent runs are separate asv invocations; repeats inside one invocation are not independent.
- Each benchmark gets a paired on/off ratio with a confidence interval from independent runs.
- Thresholds for improved, regressed and inconclusive are written in `analysis/thresholds.toml` before final runs.
