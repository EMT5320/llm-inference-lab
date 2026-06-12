# Inference Benchmark Report — mock_local

- schema_version: `bench-run-v0.1`
- run_id: `20260612T092036Z-b313dfb6`
- source: `live`
- model: `mock-model`
- base_url: `http://127.0.0.1:18080/v1`
- stream: `True`
- max_tokens: `64`

| concurrency | success | qps | agg_tps | p50_lat | p95_lat | p50_ttft | p95_ttft |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5/5 | 0.28 | 59.69 | 3.64s | 3.64s | 274.8ms | 286.2ms |
| 4 | 20/20 | 0.90 | 195.44 | 4.42s | 4.51s | 697.5ms | 1087.0ms |
| 8 | 40/40 | 1.52 | 328.96 | 5.09s | 5.55s | 1075.3ms | 2024.4ms |
