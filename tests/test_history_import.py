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
    assert len(payload["rounds"]) >= 3
    peak = max(payload["rounds"], key=lambda row: row["concurrency"])
    assert peak["concurrency"] == 16
    assert peak["aggregate_tps"] == pytest.approx(343.7)
