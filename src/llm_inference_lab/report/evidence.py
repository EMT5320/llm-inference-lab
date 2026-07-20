"""Evidence-class constants and compatibility normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

HISTORICAL_IMPORTED = "historical/imported"
LIVE_RERUN = "live/rerun"
PENDING_RERUN = "pending/rerun"
LEGACY_PENDING_OWNER_RERUN = "pending/owner-rerun"


def normalize_evidence_class(record: Mapping[str, Any]) -> str:
    """Return the canonical evidence class without upgrading legacy pending data."""
    evidence_class = str(record.get("evidence_class") or "").strip().lower()
    if evidence_class in {HISTORICAL_IMPORTED, LIVE_RERUN, PENDING_RERUN}:
        return evidence_class
    if evidence_class == LEGACY_PENDING_OWNER_RERUN:
        return PENDING_RERUN

    source = str(record.get("source") or "live").strip().lower()
    if source in {"history", "historical", "imported"}:
        return HISTORICAL_IMPORTED
    if source == "pending":
        return PENDING_RERUN
    return LIVE_RERUN
