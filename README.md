# LLM Inference Lab

Benchmark OpenAI-compatible LLM endpoints for throughput and latency: an endpoint registry, a concurrent benchmark runner (QPS, aggregate TPS, P50/P95, TTFT), historical A10/vLLM result import, and a Markdown leaderboard export.

**Headline result:** archived Gemma4 26B-A4B on 4×A10 reached a peak aggregate throughput of **343.7 tok/s** at concurrency 16 (`historical/imported`; see [Key results](#key-results-from-archived-a10-runs)). A CPU mock server validates the runner end-to-end with no GPU dependency.

Infra companion to AlgoCoach-Flywheel (sibling repo `leetcode_agent_assistant`), focused on **serving pressure tests**. Scope boundary: this repo is adjacent evidence for model serving, cost/latency tradeoffs, and endpoint selection inside Agent / evaluation systems. It is not a coaching eval orchestrator, standalone AI Infra platform, scheduler, Kubernetes stack, monitoring dashboard, or production serving product.

## What

- Register baseline / SFT / DPO / frontier OpenAI-compatible endpoints
- Run concurrent benchmarks (QPS, aggregate TPS, P50/P95 latency, TTFT via streaming)
- Import archived Gemma4 A10 performance tables and legacy qwopus JSON
- Export JSON + Markdown reports and a combined leaderboard
- Keep `historical/imported`, `live/rerun`, and `pending/owner-rerun` rows separate so imported A10 numbers do not contaminate live rerun claims

## Install

```powershell
cd <repo>
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
```

## Quickstart (CPU mock smoke)

Terminal 1:

```powershell
illab-mock --port 18080
```

Terminal 2:

```powershell
New-Item -ItemType Directory -Force -Path .run\bench\demo\history | Out-Null
illab-import-history --gemma4-md tests\fixtures\gemma4_perf_reference.sample.md `
  --output-dir .run\bench\demo\history
illab-bench --registry config/endpoints.example.json --endpoint mock_local `
  --concurrency 1,4,8 --requests-per-worker 5 --max-tokens 64 `
  --output .run\bench\demo\mock_bench_20260704.json
illab-leaderboard --history .run\bench\demo\history --runs .run\bench\demo `
  --output .run\bench\demo\inference_leaderboard_20260704.md
pytest -q
```

Or run the bundled demo:

```powershell
.\scripts\demo_mock_bench.ps1
# In offline/dev shells with dependencies already installed:
.\scripts\demo_mock_bench.ps1 -UseCurrentPython
```

## Key results (from archived A10 runs)

Historical Gemma4 26B-A4B on 4×A10 (imported from the bundled `tests/fixtures/gemma4_perf_reference.sample.md` excerpt; full run archived by owner):

- Peak aggregate throughput: **343.7 tok/s** at concurrency 16
- Single-request TPS: ~60 tok/s in the bundled excerpt; TTFT ~25–30ms

Live mock runs validate the runner on CPU without GPU dependencies.

## Evidence Classes

Leaderboard rows use explicit evidence labels:

| evidence | Meaning | Claim boundary |
|---|---|---|
| `historical/imported` | Imported from retained benchmark artifacts | Useful for interview discussion, not a current live rerun |
| `live/rerun` | Produced by current `illab-bench` execution | May be used as live runner evidence for that endpoint and environment |
| `pending/owner-rerun` | Template or model awaiting owner GPU rerun | No numeric throughput / latency claim |

Reports summarize four axes: throughput (`qps`, `aggregate_tps`), latency (`P50/P95`, TTFT), memory/hardware (`hardware`, `gpu_telemetry`), and concurrency success (`success_count`, `success_rate`). Historical rows keep their imported hardware note; live GPU memory / power telemetry should be attached only after an owner rerun.

## Endpoint registry

Example registry: [`config/endpoints.example.json`](config/endpoints.example.json)

| endpoint_id | role | env prefix |
|---|---|---|
| `base_7b` | baseline | `ILL_BASE_7B_*` |
| `coach_sft_7b` | SFT | `ILL_SFT_7B_*` |
| `coach_dpo_7b` | DPO | `ILL_DPO_7B_*` |
| `frontier_teacher` | frontier | `ILL_FRONTIER_*` |
| `vllm_7b_a10_template` | owner rerun template | `ILL_VLLM_7B_*` |
| `vllm_14b_a10_template` | owner rerun template | `ILL_VLLM_14B_*` |
| `vllm_26b_moe_a10_template` | owner rerun template | `ILL_VLLM_26B_MOE_*` |
| `mock_local` | CPU smoke | built-in `127.0.0.1:18080` |

Field layout mirrors AlgoCoach `config/endpoint_registry.phase_b.json` but uses `ILL_*` env vars and drops coaching-specific local rule rows.

## vLLM Owner Rerun Recipe

The template endpoints in `config/endpoints.example.json` document suggested A10 reruns without claiming they have been executed. Adjust model paths, ports, tensor parallel size, and context length to the actual server.

Example 7B run:

```powershell
$env:ILL_VLLM_7B_BASE_URL = "http://127.0.0.1:18087/v1"
$env:ILL_VLLM_7B_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
python -m vllm.entrypoints.openai.api_server `
  --model $env:ILL_VLLM_7B_MODEL `
  --served-model-name $env:ILL_VLLM_7B_MODEL `
  --host 0.0.0.0 --port 18087 `
  --tensor-parallel-size 1 `
  --gpu-memory-utilization 0.90 `
  --max-model-len 32768
```

Example benchmark plus telemetry uses two terminals so GPU sampling overlaps the benchmark.

Terminal A:

```powershell
python scripts/sample_nvidia_smi.py --interval 1 --duration 180 --output .run/bench/vllm_7b_a10_telemetry.jsonl
```

Terminal B:

```powershell
illab-bench --registry config/endpoints.example.json --endpoint vllm_7b_a10_template `
  --concurrency 1,4,8,16 --requests-per-worker 5 --max-tokens 256 `
  --output reports/eval/vllm_7b_a10_rerun.json
illab-leaderboard --output reports/eval/inference_leaderboard_latest.md
```

For 14B and 26B MoE, use `vllm_14b_a10_template` and `vllm_26b_moe_a10_template`; the registry records suggested tensor parallel and concurrency levels. Treat all template rows as `pending/owner-rerun` until the JSON report and telemetry artifact exist.

## CLI

| Command | Purpose |
|---|---|
| `illab-mock` | Start mock OpenAI-compatible server |
| `illab-registry` | Print endpoint readiness JSON |
| `illab-bench` | Run benchmark against registry endpoint or `--base-url` |
| `illab-import-history` | Import Gemma4 markdown / qwopus JSON |
| `illab-leaderboard` | Merge history + live runs into Markdown |
| `python scripts/sample_nvidia_smi.py` | Optional no-dependency GPU telemetry sampler for owner reruns |

## Artifact layout

- `reports/eval/` — retained benchmark JSON/Markdown and leaderboards
- `.run/bench/` — per-request detail JSONL (gitignored)
- `data/history/` — imported historical records

## Limitations

- No Web UI, scheduler, or monitoring dashboard
- TTFT requires streaming; non-streaming endpoints report TTFT ≈ total latency
- Qwopus35 historical JSON is not archived yet; leaderboard shows a pending row until GPU rerun
- Does not bundle vLLM/torch; point registry env vars at your existing servers

## Tests

```powershell
pytest -q
python -m compileall -q src tests
```

## License

MIT. See [`LICENSE`](LICENSE).
