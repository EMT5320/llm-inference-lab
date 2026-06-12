# AGENTS.md — LLM Inference Lab

## Scope

Standalone inference benchmarking repo. Not coupled to AlgoCoach runtime at import time.

## Artifact rules

- Final reports → `reports/eval/`
- Intermediate per-request traces → `.run/bench/`
- Imported history → `data/history/`

## Claim boundary

- Quote throughput/latency numbers only from measured runs or imported source files with provenance.
- Do not attach AlgoCoach coaching-quality claims to inference benchmark outputs.

## Verification

```powershell
pip install -e ".[dev]"
pytest -q
.\scripts\demo_mock_bench.ps1
```
