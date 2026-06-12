# LLM Inference Lab

Endpoint registry, OpenAI-compatible inference benchmarking, historical A10/vLLM result import, and Markdown leaderboard export.

Infra companion to [AlgoCoach-Flywheel](https://github.com/example/algocoach-flywheel) — this repo focuses on **serving pressure tests**, not coaching eval orchestration.

## What

- Register baseline / SFT / DPO / frontier OpenAI-compatible endpoints
- Run concurrent benchmarks (QPS, aggregate TPS, P50/P95 latency, TTFT via streaming)
- Import archived Gemma4 A10 performance tables and legacy qwopus JSON
- Export JSON + Markdown reports and a combined leaderboard

## Install

```powershell
cd d:\workspace\research\llm-inference-lab
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
illab-import-history --gemma4-md ..\leetcode_agent_assistant\.run\job\gemma4_perf_reference.md
illab-bench --registry config/endpoints.example.json --endpoint mock_local `
  --concurrency 1,4,8 --requests-per-worker 5 --max-tokens 64 `
  --output reports/eval/mock_bench_20260612.json
illab-leaderboard --output reports/eval/inference_leaderboard_20260612.md
pytest -q
```

Or run the bundled demo:

```powershell
.\scripts\demo_mock_bench.ps1
```

## Key results (from archived A10 runs)

Historical Gemma4 26B-A4B on 4×A10 (imported from `gemma4_perf_reference.md`):

- Peak aggregate throughput: **343.7 tok/s** at concurrency 16
- Single-request TPS: ~63–65 tok/s; TTFT ~25–30ms

Live mock runs validate the runner on CPU without GPU dependencies.

## Endpoint registry

Example registry: [`config/endpoints.example.json`](config/endpoints.example.json)

| endpoint_id | role | env prefix |
|---|---|---|
| `base_7b` | baseline | `ILL_BASE_7B_*` |
| `coach_sft_7b` | SFT | `ILL_SFT_7B_*` |
| `coach_dpo_7b` | DPO | `ILL_DPO_7B_*` |
| `frontier_teacher` | frontier | `ILL_FRONTIER_*` |
| `mock_local` | CPU smoke | built-in `127.0.0.1:18080` |

Field layout mirrors AlgoCoach `config/endpoint_registry.phase_b.json` but uses `ILL_*` env vars and drops coaching-specific local rule rows.

## CLI

| Command | Purpose |
|---|---|
| `illab-mock` | Start mock OpenAI-compatible server |
| `illab-registry` | Print endpoint readiness JSON |
| `illab-bench` | Run benchmark against registry endpoint or `--base-url` |
| `illab-import-history` | Import Gemma4 markdown / qwopus JSON |
| `illab-leaderboard` | Merge history + live runs into Markdown |

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
