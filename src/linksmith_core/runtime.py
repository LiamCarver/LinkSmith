from __future__ import annotations

from collections.abc import Mapping

from .artifacts import load_port_inputs, output_matches_port_contract, write_port_outputs
from .errors import ConfigurationError, ServiceExecutionError
from .logging import log_stage
from .models import (
    JsonArtifact,
    JsonOutput,
    MarkdownDirectoryOutput,
    PortContract,
    ServiceContext,
    ServiceRunRequest,
    ServiceRunResult,
)
from .schemas import SchemaValidator
from .service import LinkSmithService


def run_service(service: LinkSmithService, request: ServiceRunRequest) -> ServiceRunResult:
    contract = service.contract
    context = ServiceContext(
        service_name=contract.service_id,
        working_directory=request.working_directory,
    )
    validator = SchemaValidator(base_dir=request.schema_base_dir)
    log_stage(context, "runtime", "Starting service run", service=contract.service_id)
    loaded_inputs = _load_inputs(contract.inputs, request, validator, context)
    try:
        raw_outputs = service.execute(loaded_inputs, context)
    except Exception as exc:
        if isinstance(exc, Exception) and exc.__class__.__module__.startswith("linksmith_core"):
            raise
        raise ServiceExecutionError(
            f"Service '{contract.service_id}' failed during execution: {exc}"
        ) from exc
    written = _write_outputs(contract.outputs, raw_outputs, request, validator, context)
    log_stage(context, "runtime", "Completed service run", service=contract.service_id)
    return ServiceRunResult(
        service_name=contract.service_id,
        written_outputs=written,
        logs=tuple(context.logs),
    )


def _load_inputs(
    ports: tuple[PortContract, ...],
    request: ServiceRunRequest,
    validator: SchemaValidator,
    context: ServiceContext,
) -> dict[str, tuple[object, ...]]:
    incoming = {name: _normalize_request_paths(value) for name, value in request.inputs.items()}
    expected = {port.name for port in ports}
    unknown = sorted(set(incoming) - expected)
    if unknown:
        raise ConfigurationError(f"Unknown input ports: {', '.join(unknown)}")
    loaded: dict[str, tuple[object, ...]] = {}
    for port in ports:
        provided = incoming.get(port.name)
        if provided is None:
            if port.required:
                raise ConfigurationError(f"Missing required input port '{port.name}'.")
            loaded[port.name] = tuple()
            continue
        log_stage(context, "load", "Loading input port", port=port.name)
        artifacts = load_port_inputs(port, provided)
        if port.schema_ref is not None:
            for artifact in artifacts:
                if isinstance(artifact, JsonArtifact):
                    validator.validate(artifact.data, port.schema_ref)
        loaded[port.name] = artifacts
    return loaded


def _write_outputs(
    ports: tuple[PortContract, ...],
    raw_outputs: Mapping[str, object],
    request: ServiceRunRequest,
    validator: SchemaValidator,
    context: ServiceContext,
) -> dict[str, tuple[object, ...]]:
    expected = {port.name for port in ports}
    unknown = sorted(set(raw_outputs) - expected)
    if unknown:
        raise ConfigurationError(f"Unknown output ports returned by service: {', '.join(unknown)}")
    written: dict[str, tuple[object, ...]] = {}
    for port in ports:
        if port.name not in raw_outputs:
            if port.required:
                raise ConfigurationError(f"Service did not return required output port '{port.name}'.")
            written[port.name] = tuple()
            continue
        payload = raw_outputs[port.name]
        items = _iter_outputs(payload)
        if not items:
            if port.required:
                raise ConfigurationError(f"Output port '{port.name}' did not produce any artifacts.")
            written[port.name] = tuple()
            continue
        for item in items:
            if not output_matches_port_contract(port, item):
                raise ConfigurationError(
                    f"Output port '{port.name}' returned '{type(item).__name__}', "
                    f"which does not match declared type '{port.type}' and mode '{port.mode}'."
                )
            if port.schema_ref is not None and isinstance(item, JsonOutput):
                validator.validate(item.data, port.schema_ref)
            if isinstance(item, MarkdownDirectoryOutput) and port.mode != "directory":
                raise ConfigurationError(
                    f"Output port '{port.name}' returned a directory payload but is not a directory port."
                )
        port_root = request.output_root / port.name
        log_stage(context, "write", "Writing output port", port=port.name)
        paths = write_port_outputs(port, payload, port_root)
        written[port.name] = paths
    return written


def _normalize_request_paths(value: object) -> tuple:
    if isinstance(value, tuple):
        return value
    return (value,)


def _iter_outputs(payload: object) -> tuple[object, ...]:
    if isinstance(payload, tuple):
        return payload
    return (payload,)
