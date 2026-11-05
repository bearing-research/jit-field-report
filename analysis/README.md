# Analysis

- `thresholds.toml`: improved, regressed, no-effect and inconclusive rules. Values are proposed; freeze them before final runs.
- `paired.py`: paired on/off ratios per benchmark and pipeline from a tidy CSV (`benchmark,params,run,arm,time_s`), t-interval on the mean log ratio, classification from `thresholds.toml`. Confidence intervals come from independent runs only.
- `test_paired.py`: synthetic checks. Run with `python -m pytest analysis`.
- Every benchmark on `benchmarks/selected.txt` appears in the report, including null, inconclusive and insufficient results and benchmark failures.
- RQ2 profiling covers a selected set (largest wins, largest regressions, a few neutral cases) with `perf` and `-X perf` on both arms. It explains results; it is never the headline.

Dependencies for analysis (any machine, not the benchmark host): `pandas`, `numpy`, `scipy`, `pytest`.

Still to write in the pilot: a converter from asv result JSON to the tidy CSV.
