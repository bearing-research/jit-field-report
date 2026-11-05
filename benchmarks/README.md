# pandas asv benchmarks

`selected.txt` is the pre-committed benchmark list. It is committed before any final run, and only benchmarks on it are reported, including null and inconclusive ones. Changes after the first final run go in its CHANGES block with a reason.

## Setup

1. Check out pandas at `[pandas] commit` from `pins.toml`; the asv suite in `asv_bench/` comes from the same commit.
2. Install that pandas into the pinned JIT build, with NumPy and pyarrow from the pinned wheels.
3. Point asv at that interpreter with an `existing:` environment, since the repo default is a rattler environment.
4. Run each arm with `PYTHON_JIT=0` or `PYTHON_JIT=1` and log `scripts/check_jit.py` output from inside a benchmark process.

Week 1 checks, before any final run:

- [ ] `PYTHON_JIT` reaches asv's benchmark subprocesses (the `check_jit` log answers it). If not, use two builds from the same commit.
- [ ] Wall time of one paired run of the selected set on the bare-metal host.
- [ ] Run-to-run spread, to set the number of independent paired runs.

## Statistics

- Independent runs are separate asv invocations; repeats inside one invocation are not independent.
- Each benchmark gets a paired on/off ratio with a confidence interval from independent runs.
- Thresholds for improved, regressed and inconclusive are written in `analysis/thresholds.toml` before final runs.
