"""Endpoint registry utilities for inference benchmarking."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

REGISTRY_SCHEMA_VERSION = "endpoint-registry-v0.1"
MOCK_ENDPOINT_TYPES = {"mock"}
EXTERNAL_ENDPOINT_TYPES = {"vllm", "openai_compatible", "transformers", "external_endpoint"}
SUPPORTED_ENDPOINT_TYPES = MOCK_ENDPOINT_TYPES | EXTERNAL_ENDPOINT_TYPES
DEFAULT_MOCK_BASE_URL = "http://127.0.0.1:18080/v1"


def load_endpoint_registry(path: Path) -> dict[str, Any]:
    """Load and validate an endpoint registry JSON file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("endpoint registry must be a JSON object")
    endpoints = _normalize_endpoints(payload.get("endpoints"))
    _validate_endpoints(endpoints)
    registry = dict(payload)
    registry["schema_version"] = str(payload.get("schema_version") or REGISTRY_SCHEMA_VERSION)
    registry["endpoints"] = endpoints
    return registry


def build_endpoint_status(registry: dict[str, Any]) -> dict[str, Any]:
    """Build a compact readiness report for registered endpoints."""
    endpoints = _normalize_endpoints(registry.get("endpoints"))
    _validate_endpoints(endpoints)
    rows = [_endpoint_status(endpoint) for endpoint in endpoints]
    return {
        "schema_version": "endpoint-registry-status-v0.1",
        "registry_schema_version": str(registry.get("schema_version") or REGISTRY_SCHEMA_VERSION),
        "endpoint_count": len(rows),
        "enabled_count": sum(1 for row in rows if row["enabled"]),
        "ready_count": sum(1 for row in rows if row["readiness_status"] in {"ready", "mock"}),
        "endpoints": rows,
    }


def resolve_endpoint_connection(endpoint: dict[str, Any], *, env: dict[str, str] | None = None) -> dict[str, str]:
    """Resolve base URL, API key and served model name for one endpoint."""
    env_map = os.environ if env is None else env
    endpoint_type = str(endpoint.get("type") or "")
    endpoint_id = str(endpoint.get("endpoint_id") or "")
    base_url_env = str(endpoint.get("base_url_env") or "")
    api_key_env = str(endpoint.get("api_key_env") or "")
    model_env = str(endpoint.get("model_env") or _default_model_env(endpoint_id))

    if endpoint_type in MOCK_ENDPOINT_TYPES:
        base_url = str(endpoint.get("base_url") or env_map.get(base_url_env, DEFAULT_MOCK_BASE_URL)).rstrip("/")
    else:
        base_url = str(endpoint.get("base_url") or env_map.get(base_url_env, "")).rstrip("/")

    api_key = str(endpoint.get("api_key") or env_map.get(api_key_env, ""))
    if not api_key and not endpoint.get("requires_api_key", False):
        api_key = "local-dev-key"
    model = str(env_map.get(model_env, "") or endpoint.get("served_model_name") or endpoint.get("model") or "")
    return {
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "base_url_env": base_url_env,
        "api_key_env": api_key_env,
        "model_env": model_env,
        "endpoint_type": endpoint_type,
    }


def find_endpoint(registry: dict[str, Any], endpoint_id: str) -> dict[str, Any]:
    """Find an endpoint by ID in a loaded registry."""
    for endpoint in registry.get("endpoints", []):
        if str(endpoint.get("endpoint_id")) == endpoint_id:
            return endpoint
    raise ValueError(f"unknown endpoint_id: {endpoint_id}")


def _normalize_endpoints(raw: Any) -> list[dict[str, Any]]:
    """Support both list and mapping registry forms."""
    if isinstance(raw, list):
        return [dict(item) for item in raw]
    if isinstance(raw, dict):
        endpoints = []
        for endpoint_id, value in raw.items():
            if not isinstance(value, dict):
                raise ValueError(f"endpoint {endpoint_id} must be an object")
            item = dict(value)
            item.setdefault("endpoint_id", endpoint_id)
            endpoints.append(item)
        return endpoints
    raise ValueError("endpoint registry must contain endpoints as a list or object")


def _validate_endpoints(endpoints: list[dict[str, Any]]) -> None:
    """Validate required endpoint fields and duplicate IDs."""
    seen: set[str] = set()
    for endpoint in endpoints:
        endpoint_id = str(endpoint.get("endpoint_id") or "").strip()
        endpoint_type = str(endpoint.get("type") or "").strip()
        if not endpoint_id:
            raise ValueError("endpoint_id is required")
        if endpoint_id in seen:
            raise ValueError(f"duplicate endpoint_id: {endpoint_id}")
        seen.add(endpoint_id)
        if endpoint_type not in SUPPORTED_ENDPOINT_TYPES:
            raise ValueError(f"unsupported endpoint type for {endpoint_id}: {endpoint_type}")


def _endpoint_status(endpoint: dict[str, Any]) -> dict[str, Any]:
    """Summarize readiness without contacting network services."""
    endpoint_type = str(endpoint.get("type"))
    endpoint_id = str(endpoint.get("endpoint_id"))
    enabled = bool(endpoint.get("enabled", True))
    if not enabled:
        return {
            "endpoint_id": endpoint_id,
            "type": endpoint_type,
            "enabled": False,
            "readiness_status": "disabled",
            "missing": [],
        }
    if endpoint_type in MOCK_ENDPOINT_TYPES:
        return {
            "endpoint_id": endpoint_id,
            "type": endpoint_type,
            "enabled": True,
            "readiness_status": "mock",
            "missing": [],
            "model": endpoint.get("model"),
        }

    missing = _missing_external_requirements(endpoint)
    return {
        "endpoint_id": endpoint_id,
        "type": endpoint_type,
        "enabled": True,
        "readiness_status": "ready" if not missing else "missing_config",
        "missing": missing,
        "model": endpoint.get("model"),
        "adapter": endpoint.get("adapter"),
        "base_url_env": endpoint.get("base_url_env"),
        "api_key_env": endpoint.get("api_key_env"),
    }


def _missing_external_requirements(endpoint: dict[str, Any]) -> list[str]:
    """Find local configuration gaps for a served endpoint."""
    missing: list[str] = []
    base_url_env = str(endpoint.get("base_url_env") or "").strip()
    api_key_env = str(endpoint.get("api_key_env") or "").strip()
    adapter = str(endpoint.get("adapter") or "").strip()
    if base_url_env and not os.environ.get(base_url_env):
        missing.append(f"env:{base_url_env}")
    if endpoint.get("requires_api_key", False) and api_key_env and not os.environ.get(api_key_env):
        missing.append(f"env:{api_key_env}")
    if adapter and not Path(adapter).exists():
        missing.append(f"path:{adapter}")
    if not base_url_env and not endpoint.get("base_url"):
        missing.append("base_url")
    return missing


def _default_model_env(endpoint_id: str) -> str:
    """Return the conventional model-name override env var for an endpoint."""
    normalized = endpoint_id.upper().replace("-", "_")
    return f"ILL_{normalized}_MODEL"
