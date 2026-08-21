from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from linksmith_core.errors import ConfigurationError
from linksmith_core.models import JsonValue, PortContract
from linksmith_core.schemas import SchemaValidator

from .models import EnginePipelineDefinition, InvocationDefinition, PipelineEdge, ServicePortRef, StepDefinition


def load_pipeline_definition(
    path: Path,
    *,
    validate_schema: bool = True,
    schema_base_dir: Path | None = None,
) -> EnginePipelineDefinition:
    payload = _load_json_object(path)
    if validate_schema:
        validator = SchemaValidator(base_dir=schema_base_dir or path.parent)
        validator.validate(payload, _pipeline_schema_ref(path, schema_base_dir))
    inputs = tuple(_parse_port(item) for item in _optional_list(payload, "inputs"))
    outputs = tuple(_parse_port(item) for item in _optional_list(payload, "outputs"))
    steps = tuple(_parse_step(item) for item in _require_list(payload, "steps"))
    edges = tuple(_parse_edge(item) for item in _require_list(payload, "edges"))
    return EnginePipelineDefinition(
        pipeline_id=_require_string(payload, "id"),
        name=_optional_string(payload, "name"),
        description=_optional_string(payload, "description"),
        version=_optional_string(payload, "version"),
        inputs=inputs,
        outputs=outputs,
        steps=steps,
        edges=edges,
    )


def _parse_step(item: Any) -> StepDefinition:
    if not isinstance(item, dict):
        raise ConfigurationError("Step declarations must be JSON objects.")
    invocations = tuple(_parse_invocation(invocation) for invocation in _require_list(item, "invocations"))
    return StepDefinition(
        step_id=_require_string(item, "id"),
        description=_optional_string(item, "description"),
        invocations=invocations,
    )


def _parse_invocation(item: Any) -> InvocationDefinition:
    if not isinstance(item, dict):
        raise ConfigurationError("Invocation declarations must be JSON objects.")
    config = item.get("config", {})
    if not isinstance(config, dict):
        raise ConfigurationError("Invocation 'config' must be an object when present.")
    return InvocationDefinition(
        invocation_id=_require_string(item, "id"),
        service_id=_require_string(item, "service"),
        description=_optional_string(item, "description"),
        config={str(key): value for key, value in config.items() if isinstance(key, str)},
        inputs=tuple(_parse_port_ref(port_ref) for port_ref in _optional_list(item, "inputs")),
        outputs=tuple(_parse_port_ref(port_ref) for port_ref in _optional_list(item, "outputs")),
    )


def _parse_port_ref(item: Any) -> ServicePortRef:
    if not isinstance(item, dict):
        raise ConfigurationError("Port references must be JSON objects.")
    return ServicePortRef(
        service_port=_require_string(item, "servicePort"),
        alias=_optional_string(item, "alias"),
    )


def _parse_edge(item: Any) -> PipelineEdge:
    if not isinstance(item, dict):
        raise ConfigurationError("Edge declarations must be JSON objects.")
    return PipelineEdge(
        from_endpoint=_require_string(item, "from"),
        to_endpoint=_require_string(item, "to"),
        label=_optional_string(item, "label"),
    )


def _parse_port(item: Any) -> PortContract:
    if not isinstance(item, dict):
        raise ConfigurationError("Port declarations must be JSON objects.")
    return PortContract(
        name=_require_string(item, "name"),
        type=_require_string(item, "type"),
        mode=_require_string(item, "mode"),  # type: ignore[arg-type]
        cardinality=_require_string(item, "cardinality"),  # type: ignore[arg-type]
        description=_optional_string(item, "description"),
    )


def _load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ConfigurationError(f"Expected JSON object root in {path}")
    return payload


def _pipeline_schema_ref(path: Path, schema_base_dir: Path | None) -> str:
    if schema_base_dir is not None:
        return "schemas/pipeline.schema.json"
    return str((path.parent.parent / "schemas" / "pipeline.schema.json").resolve())


def _require_string(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Expected non-empty string '{key}'.")
    return value


def _optional_string(item: dict[str, Any], key: str) -> str | None:
    value = item.get(key)
    return value if isinstance(value, str) and value else None


def _require_list(item: dict[str, Any], key: str) -> list[Any]:
    value = item.get(key)
    if not isinstance(value, list):
        raise ConfigurationError(f"Expected list '{key}'.")
    return value


def _optional_list(item: dict[str, Any], key: str) -> list[Any]:
    value = item.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigurationError(f"Expected list '{key}' when present.")
    return value
