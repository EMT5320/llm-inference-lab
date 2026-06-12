# One-shot mock benchmark demo for LLM Inference Lab MVP acceptance.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
    .\.venv\Scripts\pip install -e ".[dev]"
}

$python = ".\.venv\Scripts\python.exe"
$mockJob = Start-Job -ScriptBlock {
    param($py, $root)
    Set-Location $root
    & $py -m llm_inference_lab.bench.mock_server --port 18080
} -ArgumentList (Resolve-Path $python), $Root

try {
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:18080/health" -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -eq 200) { break }
        } catch {}
        Start-Sleep -Milliseconds 300
    }

    $gemmaMd = Join-Path $Root "..\leetcode_agent_assistant\.run\job\gemma4_perf_reference.md"
    if (Test-Path $gemmaMd) {
        & $python -m llm_inference_lab.cli --help | Out-Null
        & $python -c "from llm_inference_lab.cli import _main_import_history; import sys; sys.exit(_main_import_history(['--gemma4-md', r'$gemmaMd']))"
    } else {
        & $python -c "from llm_inference_lab.history.import_gemma4_md import write_gemma4_history; from pathlib import Path; write_gemma4_history(Path('tests/fixtures/gemma4_perf_reference.sample.md'), Path('data/history/gemma4_a10_20260413.json'))"
    }

    & $python -c "import asyncio, sys; from pathlib import Path; from llm_inference_lab.cli import _main_bench; sys.exit(asyncio.run(_main_bench(['--registry', 'config/endpoints.example.json', '--endpoint', 'mock_local', '--concurrency', '1,4,8', '--requests-per-worker', '5', '--max-tokens', '64', '--output', 'reports/eval/mock_bench_20260612.json'])))"

    & $python -c "from llm_inference_lab.cli import _main_leaderboard; import sys; sys.exit(_main_leaderboard(['--output', 'reports/eval/inference_leaderboard_20260612.md']))"

    & $python -m pytest -q
    Write-Host "Demo completed successfully."
}
finally {
    Stop-Job $mockJob -ErrorAction SilentlyContinue
    Remove-Job $mockJob -Force -ErrorAction SilentlyContinue
}
