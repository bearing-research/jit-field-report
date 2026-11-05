# jit-field-report

An independent, reproducible evaluation of the experimental JIT compiler that ships in CPython 3.15, measured on pandas and on the test suites of popular PyPI packages.

Bearing Research, Inc. Author: Fangchen Li. Findings are the author's and do not represent the pandas project.

## Research questions

1. **RQ1, performance:** how does the 3.15 JIT change run time and peak memory of common pandas operations and representative data pipelines?
2. **RQ2, explanation:** which workload characteristics go with improvements, regressions or no effect?
3. **RQ3, compatibility:** which differential failures appear when package test suites run with the JIT on versus off?
4. **RQ4, reproducibility:** can each performance change and failure be reproduced independently under documented conditions?

## Status

Week 1 pilot. Nothing in `results/` is final until the report is published.

## Layout

| Path | What it holds |
| --- | --- |
| `pins.toml` | Every pinned version and commit. The single source of truth for reproduction. |
| `scripts/build_cpython.sh` | Builds CPython 3.15 with the JIT compiled in and off by default (`yes-off`), or the pystats diagnostic build. |
| `scripts/check_jit.py` | Logs JIT availability and enablement from inside a process, outside timed code. |
| `benchmarks/` | The pre-committed list of pandas asv benchmarks and how they are run. |
| `pipelines/` | Three end-to-end pandas pipelines and the timing harness. |
| `compat/` | The labeille cohort and the differential comparison. |
| `analysis/` | Statistics and figures. |
| `infra/` | Instance images and isolation rules. |
| `results/` | Raw results, one directory per run, with metadata. |

## Method in one paragraph

One CPython build per architecture, configured with `--enable-experimental-jit=yes-off`, so both arms run the same binary and differ only in `PYTHON_JIT=0` or `PYTHON_JIT=1`. pandas is built from one pinned commit on main. Arms are interleaved on bare-metal hosts; the number of independent paired runs comes from the pilot's measured noise. Every benchmark on the pre-committed list is reported, including null and inconclusive results. Compatibility runs use [labeille](https://github.com/devdanzin/labeille) on disposable instances. Coding agents wrote package configurations and harness glue; every reported finding was reproduced and checked by hand.

## Reproducing

See `pins.toml`, then `scripts/build_cpython.sh`. Each directory has its own README with the exact commands.

## License

MIT, see `LICENSE`.
