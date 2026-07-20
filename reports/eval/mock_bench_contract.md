# Inference Benchmark Report — mock_local

- schema_version: `bench-run-v0.1`
- run_id: `20260719T130920Z-0108620e`
- source: `live`
- evidence_class: `live/rerun`
- model: `mock-model`
- base_url: `http://127.0.0.1:18080/v1`
- stream: `True`
- max_tokens: `64`

## Four-axis Evidence

| axis | fields | status |
|---|---|---|
| throughput | `qps`, `aggregate_tps`, `token_count_coverage` | token TPS requires complete server usage |
| latency | `p50/p90/p95_latency_s`, `p50/p95_ttft_ms` | measured per concurrency round |
| memory/hardware | `hardware`, `gpu_telemetry` | CPU mock; no GPU telemetry; telemetry pending/rerun |
| concurrency success | `success_count`, `total_requests`, `success_rate` | measured per concurrency round |

## Rounds

| concurrency | success | success_rate | qps | agg_tps | token_usage | p50_lat | p90_lat | p95_lat | p50_ttft | p95_ttft |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5/5 | 100% | 0.45 | 96.83 | 100% | 2.24s | 2.25s | 2.26s | 34.4ms | 38.5ms |
| 4 | 20/20 | 100% | 1.77 | 383.24 | 100% | 2.26s | 2.29s | 2.29s | 38.8ms | 57.4ms |
| 8 | 40/40 | 100% | 3.52 | 763.99 | 100% | 2.27s | 2.31s | 2.31s | 48.5ms | 77.7ms |
