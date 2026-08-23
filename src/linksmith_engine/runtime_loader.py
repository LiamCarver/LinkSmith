from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from linksmith_core.errors import ConfigurationError
from linksmith_core.schemas import SchemaValidator

from .models import DockerRuntimeServiceDefinition, EngineRuntimeConfig
from .service_runner import DockerServiceConfig, DockerServiceRunner, ServiceRunner


def load_runtime_config(
    path: Path,
    *,
    validate_schema: bool = True,
    schema_base_dir: Path | None = None,
) -> EngineRuntimeConfig:
    payload = _load_json_object(path)
    if validate_schema:
        validator = SchemaValidator(base_dir=schema_base_dir or path.parent)
        validator.validate(payload, _runtime_schema_ref(path, schema_base_dir))

    runner_payload = _require_dict(payload, "runner")
    runner_kind = _require_string(runner_payload, "kind")
    if runner_kind != "docker":
        raise ConfigurationError(f"Unsupported runner kind '{runner_kind}'.")

    services_payload = _require_dict(runner_payload, "services")
    services = {
        service_id: _parse_docker_service(service_id, service_payload)
        for service_id, service_payload in services_payload.items()
    }
    return EngineRuntimeConfig(runner_kind="docker", docker_services=services)


def load_service_runner(runtime_config: EngineRuntimeConfig) -> ServiceRunner:
    if runtime_config.runner_kind != "docker":
        raise ConfigurationError(f"Unsupported runner kind '{runtime_config.runner_kind}'.")

    return DockerServiceRunner(
        {
            service_id: DockerServiceConfig(
                image=service.image,
                input_arguments=service.input_arguments,
                output_dir_argument=service.output_dir_argument,
                environment=service.environment,
                output_file_name_arguments=service.output_file_name_arguments,
                output_file_names=service.output_file_names,
                schema_base_dir_argument=service.schema_base_dir_argument,
                schema_base_dir_value=service.schema_base_dir_value,
                input_mount_root=service.input_mount_root,
                output_mount_root=service.output_mount_root,
                extra_args=service.extra_args,
            )
            for service_id, service in runtime_config.docker_services.items()
        }
    )


def _parse_docker_service(service_id: str, payload: Any) -> DockerRuntimeServiceDefinition:
    item = _coerce_named_dict(payload, f"runner.services.{service_id}")
    return DockerRuntimeServiceDefinition(
        image=_require_string(item, "image"),
        input_arguments=_require_string_mapping(item, "inputArguments"),
        output_dir_argument=_require_string(item, "outputDirArgument"),
        environment=_optional_string_mapping(item, "environment"),
        output_file_name_arguments=_optional_string_mapping(item, "outputFileNameArguments"),
        output_file_names=_optional_string_mapping(item, "outputFileNames"),
        schema_base_dir_argument=_optional_string(item, "schemaBaseDirArgument"),
        schema_base_dir_value=_optional_string(item, "schemaBaseDirValue"),
        input_mount_root=_optional_string(item, "inputMountRoot") or "/workspace/inputs",
        output_mount_root=_optional_string(item, "outputMountRoot") or "/workspace/outputs",
        extra_args=tuple(_optional_string_list(item, "extraArgs")),
    )


def _load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ConfigurationError(f"Expected JSON object root in {path}")
    return payload


def _runtime_schema_ref(path: Path, schema_base_dir: Path | None) -> str:
    if schema_base_dir is not None:
        return "schemas/runtime.schema.json"
    return str((path.parent.parent / "schemas" / "runtime.schema.json").resolve())


def _require_dict(item: dict[str, Any], key: str) -> dict[str, Any]:
    value = item.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Expected object '{key}'.")
    return value


def _coerce_named_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigurationError(f"Expected object '{name}'.")
    return value


def _require_string(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Expected non-empty string '{key}'.")
    return value


def _optional_string(item: dict[str, Any], key: str) -> str | None:
    value = item.get(key)
    return value if isinstance(value, str) and value else None


def _require_string_mapping(item: dict[str, Any], key: str) -> dict[str, str]:
    value = item.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Expected object '{key}'.")
    result: dict[str, str] = {}
    for nested_key, nested_value in value.items():
        if not isinstance(nested_key, str) or not isinstance(nested_value, str) or not nested_value:
            raise ConfigurationError(f"Expected string mapping entries in '{key}'.")
        result[nested_key] = nested_value
    return result


def _optional_string_mapping(item: dict[str, Any], key: str) -> dict[str, str]:
    value = item.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigurationError(f"Expected object '{key}'.")
    result: dict[str, str] = {}
    for nested_key, nested_value in value.items():
        if not isinstance(nested_key, str) or not isinstance(nested_value, str) or not nested_value:
            raise ConfigurationError(f"Expected string mapping entries in '{key}'.")
        result[nested_key] = nested_value
    return result


def _optional_string_list(item: dict[str, Any], key: str) -> list[str]:
    value = item.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigurationError(f"Expected list '{key}'.")
    result: list[str] = []
    for entry in value:
        if not isinstance(entry, str) or not entry:
            raise ConfigurationError(f"Expected non-empty strings in '{key}'.")
        result.append(entry)
    return result
