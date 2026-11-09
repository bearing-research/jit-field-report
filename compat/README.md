# Compatibility (labeille)

Runs package test suites with the JIT off and on, using [labeille](https://github.com/devdanzin/labeille) at the commit pinned in `pins.toml`, with per-test comparison from pytest JUnit XML.

## Cohort

`cohort.txt`: the pandas test suite first, then the top 25 packages from the dated snapshot in `pins.toml`. Excluded packages stay in the denominator with a reason. No backfilling.

All 25 are in the laruche registry (checked Nov 8 against laruche `01d8860a`, Jul 13). 23 run `python -m pytest`; pycparser uses `unittest discover`; pydantic-core has no test command. Registry `skip_versions: 3.15` notes on numpy, pydantic and pydantic-core predate their cp315 wheels and are re-checked rather than trusted.

## What labeille gives and does not give (checked Nov 8, labeille `58fdf6ab`, Apr 2)

- **JIT-off arm: yes, in `run`.** `build_env` sets `PYTHON_JIT=1` and then applies `--env` overrides, so `labeille run --env PYTHON_JIT=0` is the off arm. `bench` conditions are not needed.
- **Per-test outcomes: no.** `PackageResult` is one status per package (`pass`, `fail`, `crash`, `timeout`, `install_error`, `clone_error`, `error`) plus `exit_code`, `crash_signature`, a 2,000-character `stderr_tail`, `git_revision` and `installed_dependencies`. Test stdout is not saved (debug log only). Full stderr is saved only on a crash. So two different failures in the same test, or a JIT regression inside an already-failing package, are invisible to `analyze compare`.
- **Per-run provenance: yes.** `git_revision` and `installed_dependencies` are recorded per package per run; `--work-dir` reuses one clone for both arms so they test the same checkout.
- **Last commit April 2, 2026.** The project is alpha and has been quiet for seven months; pin the commit and expect to patch locally rather than wait for fixes.

## Per-test capture

Tests run with the package's repo clone as cwd, so a relative `--junitxml` path lands in the clone, one file per arm:

```
labeille run --top 25 --work-dir /work --env PYTHON_JIT=0 \
    --test-command-suffix "--junitxml=junit-off.xml" --results-dir results/off
labeille run --top 25 --work-dir /work --env PYTHON_JIT=1 \
    --test-command-suffix "--junitxml=junit-on.xml"  --results-dir results/on
python compat/compare_junit.py /work/repos --out results/<run>/compat
```

`compare_junit.py` classifies each test id across both arms (and across reruns, as `junit-on-2.xml` and so on): no differential failure, pre-existing (same signature both arms), masked candidate (both fail, different signatures), candidate, intermittent candidate, flaky in both, anomaly, skipped, skip differs, and collected-in-one-arm-only (a crash truncates the file: pytest writes JUnit XML at exit). Signatures are the exception class plus the first message line with addresses, sizes, durations and temp paths normalised. Tests: `python -m pytest compat`.

Caveats to handle in the pilot:

- The suffix is appended to the registry's `test_command`; it works for every `python -m pytest ...` command. pycparser's `unittest discover` needs `--test-command-override` with `python -m pytest tests/` (pytest collects unittest cases) or a `unittest-xml-reporting` runner.
- labeille's package-level status remains the authority for `crash`, `timeout` and `install_error`; JUnit XML only exists when pytest exited normally.
- Intermittent candidates: rerun 10 on and 10 off with `--test-command-suffix "--junitxml=junit-on-N.xml"` and compare the trigger rates (see Workstream 3 in the plan).

## Week 1 checks

- [x] A JIT-off arm is possible in `run` (`--env PYTHON_JIT=0`).
- [x] Per-test identifiers and outcomes: not from labeille; captured with `--junitxml` and compared by `compare_junit.py`.
- [x] Package commit and resolved dependency versions recorded per run (`git_revision`, `installed_dependencies`).
- [ ] labeille runs on the pinned build for three packages (needs the build; do this on the first spot instance).
- [ ] pycparser per-test capture confirmed with the override.

## Evidence levels

Reported with a denominator at each level: installs, tests execute, no differential failure, JIT activity observed (pystats build, sample of five packages), reproduced regression.

## Isolation

Install scripts and tests run arbitrary code. Runs happen only on disposable spot instances with no instance role, no cloud credentials and no keys to other hosts. See `infra/README.md`.
