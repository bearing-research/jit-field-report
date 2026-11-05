# Pipelines

Exactly three end-to-end pipelines, each a module with `run(data_dir) -> DataFrame`, all on one month of NYC TLC yellow taxi trips (January 2024, 2,964,624 rows) plus the taxi zone lookup. Inputs, checksums and row counts are pinned in `data/MANIFEST.toml`; fetch them with `python scripts/fetch_data.py`.

| Module | Primary behavior | Prior Python share | Output |
| --- | --- | --- | --- |
| `data_prep.py` | Read, clean, transform, filter: renames, boolean masks, datetime accessors, dict map, string concat, categoricals | mixed | about 2.75M rows x 16 columns |
| `relational.py` | Two joins to the zone lookup, groupby with built-in aggregations, transform share | native | about 900 rows x 12 columns |
| `python_heavy.py` | groupby.apply with a per-zone UDF, lambda aggregations, row-wise apply on the first 100,000 trips, per-group lag and rolling features | py | about 250 rows x 14 columns |

`common.py` holds the shared reading and cleaning step.

## Rules

- JIT-on and JIT-off outputs must hash identically (`harness.output_hash`). A mismatch is a finding, not noise.
- **fresh** mode: new interpreter per repetition, file cache warm, JIT warmup included.
- **warm** mode: warmup and measured iteration counts set in the pilot and recorded in each result.
- Peak RSS is recorded per process.

## Running

```
python scripts/fetch_data.py
PYTHON_JIT=1 python -m pipelines.harness python_heavy --data-dir data --mode warm --warmup 3 --repeat 10 --out results/<run>/python_heavy-on.json
```

## Sandbox smoke test (Nov 4, 2026)

Ran on uv's CPython 3.15.0 (aarch64, built `yes-off`) with pandas 3.1.1, NumPy 2.5.4 and pyarrow 26.0.0, one warmup and two measured calls per arm. All three pipelines ran with FutureWarning and DeprecationWarning raised as errors, and each produced the same output hash with the JIT off and on. Timings from that sandbox are not meaningful and are not reported.
