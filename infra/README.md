# Infrastructure

| Role | Instance | Purchase | Notes |
| --- | --- | --- | --- |
| Benchmarks, pipelines, profiling (x86_64) | c7i.metal-24xl | on-demand | Timed runs never on spot |
| Benchmarks (aarch64) | c7g.metal | on-demand | Only after the pilot gate |
| Builds, labeille runs | c7i.4xlarge | spot | Disposable |

## Images

One AMI per architecture with LLVM 21 and the pinned CPython build, made from `scripts/build_cpython.sh`. Record the AMI ID per run in `results/<run>/meta.json`.

## Benchmark hosts

- `pyperf system tune` before each session; record its output.
- No other workloads on the host during a run.

## Isolation for labeille hosts

- No instance profile or role attached.
- No cloud credentials, tokens or SSH keys to other hosts on the instance.
- Results leave the instance by a pull from outside, not a push with stored credentials.
- Terminate after each batch.
