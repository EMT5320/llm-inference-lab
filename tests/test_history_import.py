"""Tests for Gemma4 markdown import."""

from pathlib import Path

import pytest

from llm_inference_lab.history.import_gemma4_md import import_gemma4_markdown


GEMMA_MD = Path(__file__).resolve().parent / "fixtures" / "gemma4_perf_reference.sample.md"


def test_import_gemma4_markdown_extracts_concurrency_rows() -> None:
    payload = import_gemma4_markdown(GEMMA_MD)
    assert payload["model"] == "google/gemma-4-26B-A4B-it"
    assert payload["evidence_class"] == "historical/imported"
    assert payload["test_date"] == "2026-04-13"
    assert [row["concurrency"] for row in payload["rounds"]] == [1, 4, 16]
    assert len(payload["single_request_rows"]) == 2
    assert len(payload["output_length_rows"]) == 2
    assert payload["single_request_rows"][0]["raw"].startswith("短中文问答")
    assert payload["output_length_rows"][0]["raw"].startswith("64")
    peak = max(payload["rounds"], key=lambda row: row["concurrency"])
    assert peak["concurrency"] == 16
    assert peak["aggregate_tps"] == pytest.approx(343.7)
    assert peak["p90_latency_s"] == pytest.approx(5.49)
    assert peak["p95_latency_s"] is None
    assert peak["success_count"] is None
    assert peak["success_rate"] is None
