# Analysis

- `thresholds.toml`: improved, regressed and inconclusive thresholds, written before final runs.
- Paired on/off ratios per benchmark and pipeline, confidence intervals from independent runs only.
- Every benchmark on `benchmarks/selected.txt` appears in the report, including null and inconclusive results and benchmark failures.
- RQ2 profiling covers a selected set (largest wins, largest regressions, a few neutral cases) with `perf` and `-X perf` on both arms. It explains results; it is never the headline.
