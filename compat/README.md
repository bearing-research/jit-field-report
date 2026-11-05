# Compatibility (labeille)

Runs package test suites with the JIT off and on, using [labeille](https://github.com/devdanzin/labeille) at the commit pinned in `pins.toml`.

## Cohort

`cohort.txt`: the pandas test suite first, then the top 25 packages from the dated snapshot in `pins.toml`. Excluded packages stay in the denominator with a reason. No backfilling.

## Week 1 checks

- [ ] labeille runs on the pinned build for three packages.
- [ ] A JIT-off arm is possible (`run` sets `PYTHON_JIT=1`; `bench` takes per-condition environments).
- [ ] Per-test identifiers and outcomes in both arms, plus collected, run, passed, failed, skipped and deselected counts. If labeille cannot give these, capture pytest JUnit XML and compare with `compare_junit.py` (to write).
- [ ] Package commit and resolved dependency versions recorded per run.

## Evidence levels

Reported with a denominator at each level: installs, tests execute, JIT activity observed (pystats build, sample of five packages), no differential failure, reproduced regression.

## Isolation

Install scripts and tests run arbitrary code. Runs happen only on disposable spot instances with no instance role, no cloud credentials and no keys to other hosts. See `infra/README.md`.
