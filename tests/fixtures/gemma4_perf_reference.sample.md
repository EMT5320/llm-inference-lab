# Gemma4 sample excerpt for import tests

> 测试时间：2026-04-13

### 4.3 并发吞吐（每级 20 请求，max_tokens=256）

| 并发数 | 全局吞吐 TPS | 吞吐量 | P50 延迟 | P90 延迟 | P50 TTFT | 单请求 TPS |
|---|---|---|---|---|---|---|
| 1 | 59.3 tok/s | 0.36 req/s | 2.70s | 2.71s | 28ms | 60.6 tok/s |
| 4 | 172.1 tok/s | 1.05 req/s | 3.75s | 3.78s | 99ms | 43.8 tok/s |
| 16 | **343.7 tok/s** | 2.12 req/s | 5.35s | 5.49s | 195ms | 32.7 tok/s |
