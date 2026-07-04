# One-shot mock benchmark demo for LLM Inference Lab MVP acceptance.
param(
    [switch]$UseCurrentPython
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    # Windows PowerShell does not stop on native command failures by default.
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

function Test-PythonImports {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Python
    )

    & $Python -c "import llm_inference_lab, pytest, fastapi, httpx, uvicorn" *> $null
    return $LASTEXITCODE -eq 0
}

$previousPythonPath = $env:PYTHONPATH
$srcPath = Join-Path $Root "src"
if ($previousPythonPath) {
    $env:PYTHONPATH = "$srcPath;$previousPythonPath"
} else {
    $env:PYTHONPATH = $srcPath
}

if ($UseCurrentPython) {
    $python = "python"
} else {
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        Invoke-NativeChecked -Description "create virtual environment" -Command { python -m venv .venv }
        Invoke-NativeChecked -Description "install editable package" -Command { .\.venv\Scripts\python.exe -m pip install -e ".[dev]" }
    }
    $python = ".\.venv\Scripts\python.exe"
    if (-not (Test-PythonImports -Python $python)) {
        Invoke-NativeChecked -Description "install editable package" -Command { & $python -m pip install -e ".[dev]" }
    }
}

if (-not (Test-PythonImports -Python $python)) {
    throw "Python environment is missing required demo imports"
}

$mockJob = Start-Job -ScriptBlock {
    param($py, $root, $pythonPath)
    Set-Location $root
    $env:PYTHONPATH = $pythonPath
    & $py -m llm_inference_lab.bench.mock_server --port 18080
} -ArgumentList $python, $Root, $env:PYTHONPATH

try {
    $ready = $false
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:18080/health" -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {}
        Start-Sleep -Milliseconds 300
    }
    if (-not $ready) {
        throw "mock server did not become healthy within 15 seconds"
    }

    $demoDir = Join-Path $Root ".run\bench\demo"
    $historyDir = Join-Path $demoDir "history"
    $benchJson = Join-Path $demoDir "mock_bench_20260704.json"
    $leaderboardMd = Join-Path $demoDir "inference_leaderboard_20260704.md"
    New-Item -ItemType Directory -Force -Path $demoDir, $historyDir | Out-Null

    $gemmaMd = Join-Path $Root "tests\fixtures\gemma4_perf_reference.sample.md"
    Invoke-NativeChecked -Description "CLI help" -Command { & $python -m llm_inference_lab.cli --help | Out-Null }
    Invoke-NativeChecked -Description "import history" -Command { & $python -c "from llm_inference_lab.cli import _main_import_history; import sys; sys.exit(_main_import_history(['--gemma4-md', r'$gemmaMd', '--output-dir', r'$historyDir']))" }

    Invoke-NativeChecked -Description "mock benchmark" -Command { & $python -c "import asyncio, sys; from llm_inference_lab.cli import _main_bench; sys.exit(asyncio.run(_main_bench(['--registry', 'config/endpoints.example.json', '--endpoint', 'mock_local', '--concurrency', '1,4,8', '--requests-per-worker', '5', '--max-tokens', '64', '--output', r'$benchJson'])))" }

    Invoke-NativeChecked -Description "leaderboard export" -Command { & $python -c "from llm_inference_lab.cli import _main_leaderboard; import sys; sys.exit(_main_leaderboard(['--history', r'$historyDir', '--runs', r'$demoDir', '--output', r'$leaderboardMd']))" }

    Invoke-NativeChecked -Description "pytest" -Command { & $python -m pytest -q }
    Write-Host "Demo completed successfully."
}
finally {
    if ($null -ne $mockJob) {
        Stop-Job $mockJob -ErrorAction SilentlyContinue
        Remove-Job $mockJob -Force -ErrorAction SilentlyContinue
    }
    $env:PYTHONPATH = $previousPythonPath
}
