# Pipelines

Exactly three end-to-end pipelines, each a module with `run(data_dir) -> DataFrame`.

| Module | Primary behavior | Dataset |
| --- | --- | --- |
| `data_prep.py` | Read, clean, transform, filter | TBD in pilot |
| `relational.py` | Join, groupby, built-in aggregation | TBD in pilot |
| `python_heavy.py` | Groupby with a Python UDF, feature engineering | TBD in pilot |

Rules, fixed before final runs:

- Public datasets only, with license, source URL, file checksum and row counts recorded in `data/MANIFEST.toml`. Data files are not committed.
- JIT-on and JIT-off outputs must hash identically (`harness.output_hash`). A mismatch is a finding, not noise.
- **fresh** mode: new interpreter per repetition, file cache warm, JIT warmup included.
- **warm** mode: warmup and measured iteration counts set in the pilot and recorded in each result.
- Peak RSS is recorded per process.
