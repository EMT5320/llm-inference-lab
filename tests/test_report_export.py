"""Tests for benchmark report and leaderboard rendering."""

from llm_inference_lab.report.export import render_bench_markdown
from llm_inference_lab.report.leaderboard import render_leaderboard


def test_bench_markdown_marks_live_rerun_and_mock_hardware() -> None:
    payload = {
        "schema_version": "bench-run-v0.1",
        "run_id": "run-1",
        "source": "live",
        "endpoint_id": "mock_local",
        "model": "mock-model",
        "base_url": "http://127.0.0.1:18080/v1",
        "stream": True,
        "max_tokens": 64,
        "rounds": [
            {
                "concurrency": 4,
                "success_count": 8,
                "total_requests": 10,
                "success_rate": 0.8,
                "qps": 1.25,
                "aggregate_tps": 120.0,
                "p50_latency_s": 2.0,
                "p95_latency_s": 3.0,
                "p50_ttft_ms": 50.0,
                "p95_ttft_ms": 75.0,
            }
        ],
    }

    markdown = render_bench_markdown(payload)

    assert "evidence_class: `live/rerun`" in markdown
    assert "CPU mock; no GPU telemetry" in markdown
    assert "| 4 | 8/10 | 80% |" in markdown


def test_leaderboard_separates_imported_live_and_pending_claims() -> None:
    records = [
        {
            "source": "history",
            "model": "imported-model",
            "hardware": "4xA10-22GB",
            "test_date": "2026-04-13",
            "rounds": [
                {
                    "concurrency": 16,
                    "aggregate_tps": 343.7,
                    "qps": 2.12,
                    "p50_latency_s": 5.35,
                    "p95_latency_s": 5.49,
                    "p50_ttft_ms": 195.0,
                    "success_rate": 1.0,
                }
            ],
        },
        {
            "source": "live",
            "model": "live-model",
            "rounds": [
                {
                    "concurrency": 1,
                    "aggregate_tps": 10.0,
                    "qps": 0.5,
                    "p50_latency_s": 1.0,
                    "p95_latency_s": 1.2,
                    "p50_ttft_ms": 25.0,
                    "success_rate": 1.0,
                }
            ],
        },
    ]

    markdown = render_leaderboard(records, pending_models=["planned-gpu-rerun-model"])

    assert "historical/imported/2026-04-13" in markdown
    assert "live/rerun" in markdown
    assert "pending/rerun" in markdown
    assert "4xA10-22GB; imported" in markdown
    assert "| planned-gpu-rerun-model | pending/rerun | n/a |" in markdown
    assert "owner rerun" not in markdown.lower()


def test_legacy_pending_evidence_is_normalized_without_live_upgrade() -> None:
    payload = {
        "evidence_class": "pending/owner-rerun",
        "endpoint_id": "legacy-pending",
        "model": "legacy-pending-model",
        "rounds": [
            {
                "concurrency": 1,
                "aggregate_tps": None,
                "qps": None,
                "p50_latency_s": None,
                "p90_latency_s": None,
                "p95_latency_s": None,
                "p50_ttft_ms": None,
                "success_rate": None,
            }
        ],
    }

    report = render_bench_markdown(payload)
    leaderboard = render_leaderboard([payload])

    assert "evidence_class: `pending/rerun`" in report
    assert "| legacy-pending-model | pending/rerun |" in leaderboard
    assert "| legacy-pending-model | live/rerun |" not in leaderboard


def test_bench_markdown_keeps_missing_token_usage_as_na() -> None:
    payload = {
        "schema_version": "bench-run-v0.1",
        "run_id": "run-without-usage",
        "source": "live",
        "endpoint_id": "usage-missing",
        "model": "compatible-endpoint",
        "stream": True,
        "max_tokens": 32,
        "rounds": [
            {
                "concurrency": 1,
                "success_count": 1,
                "total_requests": 1,
                "success_rate": 1.0,
                "qps": 1.25,
                "aggregate_tps": None,
                "token_count_coverage": 0.0,
                "p50_latency_s": 0.8,
                "p90_latency_s": 0.8,
                "p95_latency_s": 0.8,
                "p50_ttft_ms": 40.0,
                "p95_ttft_ms": 40.0,
            }
        ],
    }

    markdown = render_bench_markdown(payload)

    assert "| 1 | 1/1 | 100% | 1.25 | n/a | 0% |" in markdown
