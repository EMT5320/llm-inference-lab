"""Tests for qwopus JSON import."""

import json
from pathlib import Path

from llm_inference_lab.history.import_qwopus_json import import_qwopus_json


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "qwopus_bench.sample.json"


def test_import_qwopus_json_normalizes_rounds() -> None:
    payload = import_qwopus_json(FIXTURE)
    assert payload["model"] == "qwopus35"
    assert payload["evidence_class"] == "historical/imported"
    assert len(payload["rounds"]) == 2
    assert payload["rounds"][0]["concurrency"] == 1
    assert payload["rounds"][1]["aggregate_tps"] == 172.1


def test_fixture_is_valid_json() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert "rounds" in data
