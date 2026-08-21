from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from linksmith_core.errors import ConfigurationError
from linksmith_core.models import PortContract, ServiceContract
from linksmith_core.schemas import SchemaValidator

from .models import EngineRegisteredService, EngineRegistryDocument


def load_registry_document(
    path: Path,
    *,
    validate_schema: bool = True,
    schema_base_dir: Path | None = None,
) -> EngineRegistryDocument:
    payload = _load_json_object(path)
    if validate_schema:
        validator = SchemaValidator(base_dir=schema_base_dir or path.parent)
        validator.validate(payload, _registry_schema_ref(path, schema_base_dir))
    services_payload = payload.get("services")
    if not isinstance(services_payload, list):
        raise ConfigurationError("Registry JSON must contain a 'services' array.")
    services = tuple(_parse_service(item) for item in services_payload)
    return EngineRegistryDocument(services=services)


def _parse_service(item: dict[str, Any]) -> EngineRegisteredService:
    service_id = _require_string(item, "id")
    inputs = tuple(_parse_port(port) for port in _require_list(item, "inputs"))
    outputs = tuple(_parse_port(port) for port in _require_list(item, "outputs"))
    return EngineRegisteredService(
        service_id=service_id,
        kind=_require_string(item, "kind"),
        deterministic=_require_bool(item, "deterministic"),
        description=_require_string(item, "description"),
        entrypoint=_require_string(item, "entrypoint"),
        contract=ServiceContract(service_id=service_id, inputs=inputs, outputs=outputs, version=_optional_string(item, "version")),
        config_schema=_optional_string(item, "configSchema"),
        notes=_optional_string(item, "notes"),
    )


def _parse_port(item: Any) -> PortContract:
    if not isinstance(item, dict):
        raise ConfigurationError("Port declarations must be JSON objects.")
    return PortContract(
        name=_require_string(item, "name"),
        type=_require_string(item, "type"),
        mode=_require_string(item, "mode"),  # type: ignore[arg-type]
        cardinality=_require_string(item, "cardinality"),  # type: ignore[arg-type]
        required=item.get("required", True) if isinstance(item.get("required", True), bool) else True,
        description=_optional_string(item, "description"),
        schema_ref=_optional_string(item, "schemaRef"),
    )


def _load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ConfigurationError(f"Expected JSON object root in {path}")
    return payload


def _registry_schema_ref(path: Path, schema_base_dir: Path | None) -> str:
    if schema_base_dir is not None:
        return "schemas/registry.schema.json"
    return str((path.parent.parent / "schemas" / "registry.schema.json").resolve())


def _require_string(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Expected non-empty string '{key}'.")
    return value


def _optional_string(item: dict[str, Any], key: str) -> str | None:
    value = item.get(key)
    return value if isinstance(value, str) and value else None


def _require_bool(item: dict[str, Any], key: str) -> bool:
    value = item.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"Expected boolean '{key}'.")
    return value


def _require_list(item: dict[str, Any], key: str) -> list[Any]:
    value = item.get(key)
    if not isinstance(value, list):
        raise ConfigurationError(f"Expected list '{key}'.")
    return value
