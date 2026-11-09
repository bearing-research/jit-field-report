# Analysis

- `thresholds.toml`: improved, regressed, no-effect and inconclusive rules. Values are proposed; freeze them before final runs.
- `paired.py`: paired on/off ratios per benchmark and pipeline from a tidy CSV (`benchmark,params,run,arm,time_s`), t-interval on the mean log ratio, classification from `thresholds.toml`. Confidence intervals come from independent runs only.
- `test_paired.py`: synthetic checks. Run with `python -m pytest analysis`.
- Every benchmark on `benchmarks/selected.txt` appears in the report, including null, inconclusive and insufficient results and benchmark failures.
- RQ2 profiling covers a selected set (largest wins, largest regressions, a few neutral cases). It explains results; it is never the headline.
- **`-X perf` works only in the off arm.** On the 3.15 branch `sys.activate_stack_trampoline` raises `ValueError("Cannot activate the perf trampoline if the JIT is active")` for both the `perf` and `perf_jit` backends, and `Python/jit.c` writes no perf map of its own (checked Nov 8 against `Python/sysmodule.c` and `Python/jit.c` on the 3.15 branch). So: off arm = `perf record` with `-X perf` for Python-function attribution; on arm = plain `perf record`, where JIT-compiled stencils show as anonymous executable memory. The on arm's comparison is therefore native-vs-anonymous time plus the off arm's Python attribution as the baseline, with pystats executor counts saying which code objects were compiled. Report the asymmetry explicitly.

- `asv_to_tidy.py`: converter from asv result JSON to the tidy CSV. Expands parameterised benchmarks into one row per parameter combination, keeps `time_*` and `peakmem_*` by default (`track_*` values are not timings and break `paired.py`), and writes failed or null results to `<out>-failures.csv` so they are reported. Layout it reads: `results/<run>/asv/run-NN/{off,on}.json`, one directory per independent paired run.
- `test_asv_to_tidy.py` and `testdata/asv/`: schema fixtures from asv 0.6.6 (sandbox, Nov 8, 2026; timings meaningless).

Two asv facts the converter depends on (verified Nov 8 in the sandbox):

1. asv writes one result file per (machine, commit, environment) and **overwrites it** on the next invocation with the same keys. Run the arms under different machine labels (`--machine c7i-metal-jit-off` / `-jit-on`), and move both files into `run-NN/` after every paired invocation, or the next run destroys the previous one.
2. An `existing:` environment ignores asv's env matrix, so `matrix: {"env": {"PYTHON_JIT": [...]}}` does not produce two arms. The shell's `PYTHON_JIT` does reach benchmark subprocesses, which is what makes the machine-label approach work.

Dependencies for analysis (any machine, not the benchmark host): `pandas`, `numpy`, `scipy`, `pytest`.
