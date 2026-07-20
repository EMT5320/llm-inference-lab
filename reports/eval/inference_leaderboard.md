# Inference Leaderboard

- Claim boundary: `historical/imported` rows come from imported artifacts; `live/rerun` rows come from current `illab-bench` reruns; `pending/rerun` rows carry no numeric claim.
- Four-axis scope: throughput (`agg_tps`, `qps`, `token_count_coverage`), latency (`p50/p90/p95`, `TTFT`), memory/hardware (`hardware/telemetry`), and concurrency success (`success_rate`).

| model | evidence | concurrency | agg_tps | qps | p50_lat | p90_lat | p95_lat | p50_ttft | success | hardware/telemetry | notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| google/gemma-4-26B-A4B-it | historical/imported/2026-04-13 | 1 | 59.3 | 0.4 | 2.70s | 2.71s | n/a | 28ms | n/a | 4xA10-22GB; imported | Imported from gemma4_perf_reference.md §4 concurrency sweep. |
| google/gemma-4-26B-A4B-it | historical/imported/2026-04-13 | 2 | 101.2 | 0.6 | 3.21s | 3.23s | n/a | 64ms | n/a | 4xA10-22GB; imported | Imported from gemma4_perf_reference.md §4 concurrency sweep. |
| google/gemma-4-26B-A4B-it | historical/imported/2026-04-13 | 4 | 172.1 | 1.1 | 3.75s | 3.78s | n/a | 99ms | n/a | 4xA10-22GB; imported | Imported from gemma4_perf_reference.md §4 concurrency sweep. |
| google/gemma-4-26B-A4B-it | historical/imported/2026-04-13 | 8 | 261.1 | 1.6 | 4.16s | 4.23s | n/a | 130ms | n/a | 4xA10-22GB; imported | Imported from gemma4_perf_reference.md §4 concurrency sweep. |
| google/gemma-4-26B-A4B-it | historical/imported/2026-04-13 | 16 | 343.7 | 2.1 | 5.35s | 5.49s | n/a | 195ms | n/a | 4xA10-22GB; imported | Imported from gemma4_perf_reference.md §4 concurrency sweep. |
| mock-model | live/rerun | 1 | 96.8 | 0.4 | 2.24s | 2.25s | 2.26s | 34ms | 100% | CPU mock; no GPU telemetry; telemetry pending/rerun |  |
| mock-model | live/rerun | 4 | 383.2 | 1.8 | 2.26s | 2.29s | 2.29s | 39ms | 100% | CPU mock; no GPU telemetry; telemetry pending/rerun |  |
| mock-model | live/rerun | 8 | 764.0 | 3.5 | 2.27s | 2.31s | 2.31s | 48ms | 100% | CPU mock; no GPU telemetry; telemetry pending/rerun |  |
| qwopus35-27b | pending/rerun | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | pending/rerun | planned GPU rerun; no numeric claim |
