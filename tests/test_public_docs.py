"""Regression checks for recruiter-facing public documentation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_surfaces_use_reader_facing_evidence_language() -> None:
    forbidden = (
        "pending/owner-rerun",
        "owner benchmark note",
        "explicitly authorized owner rerun",
        "LLMOps 邻接证据",
    )
    public_files = (
        "README.md",
        "config/endpoints.example.json",
        "docs/assets/inference-evidence-curve.svg",
        "reports/eval/inference_leaderboard.md",
        "reports/eval/mock_bench_contract.json",
        "reports/eval/mock_bench_contract.md",
    )
    for relative_path in public_files:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert all(phrase not in text for phrase in forbidden), relative_path

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "pending/rerun" in readme
    assert "retained benchmark artifact" in readme
    assert "planned GPU rerun" in readme
    assert "用于 OpenAI-compatible endpoint 的选型、容量评估与性能回归。" in readme


def test_readme_limitations_is_one_scoped_statement() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    limitations = readme.split("## Limitations", maxsplit=1)[1].split("## Tests", maxsplit=1)[0].strip()

    assert limitations == (
        "当前范围聚焦 benchmark runner、telemetry seam 与 evidence-class leaderboard；"
        "调度、集群编排和监控平台不在本仓范围内。"
    )