from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .errors import PipelineValidationError
from .models import (
    EndpointReference,
    EnginePipelineDefinition,
    EngineRegisteredService,
    EngineRegistryDocument,
    InvocationDefinition,
)


def validate_pipeline_semantics(
    pipeline: EnginePipelineDefinition,
    registry: EngineRegistryDocument,
) -> None:
    errors: list[str] = []
    service_index = {service.service_id: service for service in registry.services}
    step_ids: set[str] = set()
    invocation_index: dict[tuple[str, str], InvocationDefinition] = {}

    for step in pipeline.steps:
        if step.step_id in step_ids:
            errors.append(f"Duplicate step id '{step.step_id}'.")
        step_ids.add(step.step_id)
        invocation_ids: set[str] = set()
        for invocation in step.invocations:
            key = (step.step_id, invocation.invocation_id)
            if invocation.invocation_id in invocation_ids:
                errors.append(
                    f"Duplicate invocation id '{invocation.invocation_id}' inside step '{step.step_id}'."
                )
            invocation_ids.add(invocation.invocation_id)
            invocation_index[key] = invocation
            if invocation.service_id not in service_index:
                errors.append(
                    f"Invocation '{step.step_id}.{invocation.invocation_id}' references unknown service '{invocation.service_id}'."
                )
                continue
            _validate_invocation_resources(
                pipeline=pipeline,
                invocation=invocation,
                service=service_index[invocation.service_id],
                errors=errors,
            )

    incoming_edges: dict[str, list[EndpointReference]] = defaultdict(list)
    for edge in pipeline.edges:
        from_ref = _parse_endpoint(edge.from_endpoint, errors, "from")
        to_ref = _parse_endpoint(edge.to_endpoint, errors, "to")
        if from_ref is None or to_ref is None:
            continue
        _validate_endpoint_exists(from_ref, pipeline, invocation_index, service_index, errors, is_source=True)
        _validate_endpoint_exists(to_ref, pipeline, invocation_index, service_index, errors, is_source=False)
        if from_ref.kind == "pipeline_output":
            errors.append(f"Edge source '{edge.from_endpoint}' cannot be a pipeline output.")
        if to_ref.kind == "pipeline_input":
            errors.append(f"Edge target '{edge.to_endpoint}' cannot be a pipeline input.")
        source_port = _resolve_port(from_ref, pipeline, invocation_index, service_index)
        target_port = _resolve_port(to_ref, pipeline, invocation_index, service_index)
        if source_port is not None and target_port is not None:
            if source_port.type != target_port.type:
                errors.append(
                    f"Type mismatch between '{edge.from_endpoint}' ({source_port.type}) and "
                    f"'{edge.to_endpoint}' ({target_port.type})."
                )
            if source_port.mode != target_port.mode:
                errors.append(
                    f"Mode mismatch between '{edge.from_endpoint}' ({source_port.mode}) and "
                    f"'{edge.to_endpoint}' ({target_port.mode})."
                )
            if target_port.cardinality == "one" and len(incoming_edges[edge.to_endpoint]) >= 1:
                errors.append(
                    f"Target '{edge.to_endpoint}' accepts only one upstream artifact but has multiple incoming edges."
                )
            if source_port.cardinality == "many" and target_port.cardinality == "one":
                errors.append(
                    f"Target '{edge.to_endpoint}' is single-cardinality but source '{edge.from_endpoint}' is many."
                )
        incoming_edges[edge.to_endpoint].append(from_ref)

    for step in pipeline.steps:
        for invocation in step.invocations:
            service = service_index.get(invocation.service_id)
            if service is None:
                continue
            for port in service.contract.inputs:
                endpoint = f"{step.step_id}.{invocation.invocation_id}.{port.name}"
                has_resource = any(resource.name == port.name for resource in invocation.resources)
                if len(incoming_edges[endpoint]) == 0 and not has_resource:
                    errors.append(
                        f"Required service input '{endpoint}' must have an incoming edge or bound resource."
                    )
                if len(incoming_edges[endpoint]) > 0 and has_resource:
                    errors.append(
                        f"Service input '{endpoint}' cannot be bound by both an incoming edge and an invocation resource."
                    )

    for port in pipeline.outputs:
        endpoint = f"pipeline:output.{port.name}"
        if len(incoming_edges[endpoint]) == 0:
            errors.append(
                f"Declared pipeline output '{endpoint}' must have an incoming edge."
            )

    if errors:
        raise PipelineValidationError(errors)


def _validate_invocation_resources(
    *,
    pipeline: EnginePipelineDefinition,
    invocation: InvocationDefinition,
    service: EngineRegisteredService,
    errors: list[str],
) -> None:
    seen_names: set[str] = set()
    service_inputs = {port.name: port for port in service.contract.inputs}
    for resource in invocation.resources:
        if resource.name in seen_names:
            errors.append(
                f"Invocation '{invocation.service_id}' declares duplicate resource name '{resource.name}'."
            )
            continue
        seen_names.add(resource.name)
        service_port = service_inputs.get(resource.name)
        if service_port is None:
            errors.append(
                f"Invocation resource '{resource.name}' does not match an input port on service '{service.service_id}'."
            )
            continue
        if service_port.type != resource.type:
            errors.append(
                f"Invocation resource '{resource.name}' type '{resource.type}' does not match service input type '{service_port.type}'."
            )
        if service_port.mode != resource.mode:
            errors.append(
                f"Invocation resource '{resource.name}' mode '{resource.mode}' does not match service input mode '{service_port.mode}'."
            )
        if service_port.cardinality != resource.cardinality:
            errors.append(
                f"Invocation resource '{resource.name}' cardinality '{resource.cardinality}' does not match service input cardinality '{service_port.cardinality}'."
            )
        resolved = _resolve_resource_path(pipeline.definition_path, resource.path)
        if not resolved.exists():
            errors.append(
                f"Invocation resource '{resource.name}' path does not exist: {resource.path}"
            )
            continue
        if resource.mode == "file" and not resolved.is_file():
            errors.append(
                f"Invocation resource '{resource.name}' expects a file path: {resource.path}"
            )
        if resource.mode == "directory" and not resolved.is_dir():
            errors.append(
                f"Invocation resource '{resource.name}' expects a directory path: {resource.path}"
            )


def _resolve_resource_path(definition_path: Path, resource_path: str) -> Path:
    candidate = Path(resource_path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (definition_path.parent / candidate).resolve()


def _parse_endpoint(raw: str, errors: list[str], role: str) -> EndpointReference | None:
    if raw.startswith("pipeline:input."):
        return EndpointReference(kind="pipeline_input", port_name=raw.split(".", 1)[1])
    if raw.startswith("pipeline:output."):
        return EndpointReference(kind="pipeline_output", port_name=raw.split(".", 1)[1])
    parts = raw.split(".")
    if len(parts) != 3:
        errors.append(f"Invalid {role} endpoint '{raw}'.")
        return None
    return EndpointReference(
        kind="invocation",
        step_id=parts[0],
        invocation_id=parts[1],
        port_name=parts[2],
    )


def _validate_endpoint_exists(
    endpoint: EndpointReference,
    pipeline: EnginePipelineDefinition,
    invocation_index: dict[tuple[str, str], InvocationDefinition],
    service_index: dict[str, EngineRegisteredService],
    errors: list[str],
    *,
    is_source: bool,
) -> None:
    if endpoint.kind == "pipeline_input":
        if endpoint.port_name not in {port.name for port in pipeline.inputs}:
            errors.append(f"Pipeline input '{endpoint.port_name}' is not declared.")
        return
    if endpoint.kind == "pipeline_output":
        if endpoint.port_name not in {port.name for port in pipeline.outputs}:
            errors.append(f"Pipeline output '{endpoint.port_name}' is not declared.")
        return
    key = (endpoint.step_id or "", endpoint.invocation_id or "")
    invocation = invocation_index.get(key)
    if invocation is None:
        errors.append(f"Invocation endpoint '{endpoint.step_id}.{endpoint.invocation_id}' does not exist.")
        return
    service = service_index.get(invocation.service_id)
    if service is None:
        return
    ports = service.contract.outputs if is_source else service.contract.inputs
    if endpoint.port_name not in {port.name for port in ports}:
        side = "output" if is_source else "input"
        errors.append(
            f"Service '{service.service_id}' does not declare {side} port '{endpoint.port_name}'."
        )


def _resolve_port(
    endpoint: EndpointReference,
    pipeline: EnginePipelineDefinition,
    invocation_index: dict[tuple[str, str], InvocationDefinition],
    service_index: dict[str, EngineRegisteredService],
):
    if endpoint.kind == "pipeline_input":
        return next((port for port in pipeline.inputs if port.name == endpoint.port_name), None)
    if endpoint.kind == "pipeline_output":
        return next((port for port in pipeline.outputs if port.name == endpoint.port_name), None)
    invocation = invocation_index.get((endpoint.step_id or "", endpoint.invocation_id or ""))
    if invocation is None:
        return None
    service = service_index.get(invocation.service_id)
    if service is None:
        return None
    for port in service.contract.inputs + service.contract.outputs:
        if port.name == endpoint.port_name:
            return port
    return None
