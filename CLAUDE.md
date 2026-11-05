# CLAUDE.md

Instructions for a coding agent working in this repo. Read `README.md` first.

## Hard rules

1. **Never run on a labeille host.** labeille runs third-party install scripts and tests, which execute arbitrary code; your API key would be exposed. Start labeille runs on disposable instances from outside, or start them and log out.
2. **Stay idle during timed runs.** On a benchmark host, launch the final timed job and stop working until it finishes. Your own CPU load skews timings. During the pilot this is relaxed for setup and debugging, but never while a run whose numbers will be kept is in progress.
3. **Pins are the source of truth.** Use only versions and commits from `pins.toml`. Fill a "TBD" only when the pilot task says so, and add a CHANGES line for any change after a value is set.
4. **No selective reporting.** Do not add or remove entries in `benchmarks/selected.txt` or change `analysis/thresholds.toml` after a final run without a CHANGES line and a reason.
5. **No upstream activity without the author.** Do not open issues or PRs on CPython, pandas, labeille or laruche. Draft them in `results/<run>/drafts/` for Fangchen to review and file.
6. Never call `sys._jit.is_active()` in timed code.

## Week 1 pilot tasks (x86_64, c7i.metal-24xl)

- [ ] Build CPython with `scripts/build_cpython.sh`; record the commit in `pins.toml`. Also build the pystats variant (`VARIANT=pystats`).
- [ ] Pick the pandas main commit with Fangchen; build and install it into the JIT build with NumPy 2.5.4 and pyarrow 26.0.0 wheels; record the SHA.
- [ ] Run `scripts/check_jit.py` with `PYTHON_JIT=0` and `1`; confirm `jit_enabled` flips.
- [ ] Wire pandas asv to the build with an `existing:` environment. Confirm `PYTHON_JIT` reaches benchmark subprocesses by logging `check_jit.jit_state()` from inside one benchmark. If it does not, fall back to two builds from the same commit (`=yes` and `=no`).
- [ ] Re-check every name in `benchmarks/selected.txt` against the pinned pandas commit.
- [ ] Time one paired run of the selected set; run three paired runs and report the spread per benchmark.
- [ ] Write the converter from asv result JSON to the tidy CSV that `analysis/paired.py` reads.
- [ ] Run the three pipelines in both modes (`python scripts/fetch_data.py` first); confirm identical output hashes across arms.
- [ ] Confirm the pystats build reports trace and executor counts for one benchmark and one pipeline.
- [ ] Write a pilot summary in `results/pilot/SUMMARY.md`: build details, asv wiring outcome, timings, spread, and anything that blocks the plan.

## Useful facts

- `--enable-experimental-jit=yes-off` builds the JIT disabled by default; `PYTHON_JIT=1` enables it at startup.
- uv's managed CPython 3.15 (python-build-standalone) is also built `yes-off`, with the tail-calling interpreter, mimalloc and clang. It is handy for quick local checks but is not the study's build.
- pandas 3.x defaults to the `str` dtype; groupby `apply` should select columns explicitly.
- Run analysis tests with `python -m pytest analysis`.
