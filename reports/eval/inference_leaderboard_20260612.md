# Inference Leaderboard

- Claim boundary: `historical/imported` rows come from imported artifacts; `live/rerun` rows come from current `illab-bench` reruns; `pending/owner-rerun` rows carry no numeric claim.
- Four-axis scope: throughput (`agg_tps`, `qps`), latency (`p50/p95`, `TTFT`), memory/hardware (`hardware/telemetry`), and concurrency success (`success_rate`).

| model | evidence | concurrency | agg_tps | qps | p50_lat | p95_lat | p50_ttft | success | hardware/telemetry | notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| google/gemma-4-26B-A4B-it | historical/imported/2026-04-13 | 1 | 59.3 | 0.4 | 2.70s | 2.71s | 28ms | 100% | 4xA10-22GB; imported | Imported from gemma4_perf_reference.md §4 concurrency sweep. |
| google/gemma-4-26B-A4B-it | historical/imported/2026-04-13 | 2 | 101.2 | 0.6 | 3.21s | 3.23s | 64ms | 100% | 4xA10-22GB; imported | Imported from gemma4_perf_reference.md §4 concurrency sweep. |
| google/gemma-4-26B-A4B-it | historical/imported/2026-04-13 | 4 | 172.1 | 1.1 | 3.75s | 3.78s | 99ms | 100% | 4xA10-22GB; imported | Imported from gemma4_perf_reference.md §4 concurrency sweep. |
| google/gemma-4-26B-A4B-it | historical/imported/2026-04-13 | 8 | 261.1 | 1.6 | 4.16s | 4.23s | 130ms | 100% | 4xA10-22GB; imported | Imported from gemma4_perf_reference.md §4 concurrency sweep. |
| google/gemma-4-26B-A4B-it | historical/imported/2026-04-13 | 16 | 343.7 | 2.1 | 5.35s | 5.49s | 195ms | 100% | 4xA10-22GB; imported | Imported from gemma4_perf_reference.md §4 concurrency sweep. |
| mock-model | live/rerun | 1 | 59.7 | 0.3 | 3.64s | 3.64s | 275ms | 100% | CPU mock; no GPU telemetry |  |
| mock-model | live/rerun | 4 | 195.4 | 0.9 | 4.42s | 4.51s | 698ms | 100% | CPU mock; no GPU telemetry |  |
| mock-model | live/rerun | 8 | 329.0 | 1.5 | 5.09s | 5.55s | 1075ms | 100% | CPU mock; no GPU telemetry |  |
| qwopus35-27b | pending/owner-rerun | n/a | n/a | n/a | n/a | n/a | n/a | n/a | pending/owner-rerun | owner rerun required; no numeric claim |
