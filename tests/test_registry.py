"""Tests for endpoint registry."""

from pathlib import Path

import pytest

from llm_inference_lab.endpoint_registry import build_endpoint_status, find_endpoint, load_endpoint_registry


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "endpoints.example.json"


def test_registry_loads_and_has_mvp_endpoints() -> None:
    registry = load_endpoint_registry(REGISTRY)
    ids = {item["endpoint_id"] for item in registry["endpoints"]}
    assert {"mock_local", "base_7b", "coach_sft_7b", "coach_dpo_7b", "frontier_teacher"}.issubset(ids)
    assert {"vllm_7b_a10_template", "vllm_14b_a10_template", "vllm_26b_moe_a10_template"}.issubset(ids)


def test_mock_endpoint_is_ready() -> None:
    report = build_endpoint_status(load_endpoint_registry(REGISTRY))
    mock_row = next(row for row in report["endpoints"] if row["endpoint_id"] == "mock_local")
    assert mock_row["readiness_status"] == "mock"


def test_find_endpoint_unknown_raises() -> None:
    registry = load_endpoint_registry(REGISTRY)
    with pytest.raises(ValueError, match="unknown endpoint_id"):
        find_endpoint(registry, "missing")
