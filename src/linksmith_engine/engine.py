from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Mapping

from linksmith_core.errors import ConfigurationError, MalformedJsonError
from linksmith_core.models import PortContract
from linksmith_core.schemas import SchemaValidator

from .manifest import write_invocation_manifest, write_run_manifest
from .models import (
    EndpointReference,
    EnginePipelineDefinition,
    EngineRegistryDocument,
    InvocationDefinition,
    InvocationManifest,
    RunManifest,
)
from .pipeline_loader import load_pipeline_definition
from .registry_loader import load_registry_document
from .run_layout import RunPaths, create_run_layout
from .service_runner import ServiceRunner, ServiceRunnerRequest
from .validator import validate_pipeline_semantics


class PipelineRunRequest:
    def __init__(
        self,
        *,
        pipeline_path: Path,
        registry_path: Path,
        pipeline_inputs: Mapping[str, Path | tuple[Path, ...]],
        run_root: Path,
        service_runner: ServiceRunner,
        run_id: str | None = None,
        validate_schema: bool = False,
        validate_outputs: bool = False,
    ) -> None:
        self.pipeline_path = pipeline_path
        self.registry_path = registry_path
        self.pipeline_inputs = dict(pipeline_inputs)
        self.run_root = run_root
        self.service_runner = service_runner
        self.run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
        self.validate_schema = validate_schema
        self.validate_outputs = validate_outputs


class PipelineRunResult:
    def __init__(
        self,
        *,
        run_paths: RunPaths,
        pipeline: EnginePipelineDefinition,
        outputs: Mapping[str, tuple[Path, ...]],
        invocation_manifests: tuple[Path, ...],
    ) -> None:
        self.run_paths = run_paths
        self.pipeline = pipeline
        self.outputs = dict(outputs)
        self.invocation_manifests = invocation_manifests


def run_pipeline(request: PipelineRunRequest) -> PipelineRunResult:
    registry = load_registry_document(
        request.registry_path,
        validate_schema=request.validate_schema,
        schema_base_dir=request.registry_path.parent.parent if request.validate_schema else None,
    )
    pipeline = load_pipeline_definition(
        request.pipeline_path,
        validate_schema=request.validate_schema,
        schema_base_dir=request.pipeline_path.parent.parent if request.validate_schema else None,
    )
    validate_pipeline_semantics(pipeline, registry)
    run_paths = create_run_layout(request.run_root, request.run_id, request.pipeline_path, request.registry_path)
    pipeline_input_artifacts = _materialize_pipeline_inputs(run_paths, pipeline, request.pipeline_inputs)

    service_index = {service.service_id: service for service in registry.services}
    produced_artifacts: dict[str, tuple[Path, ...]] = {}
    invocation_manifest_paths: list[Path] = []
    remaining = {(step.step_id, invocation.invocation_id): invocation for step in pipeline.steps for invocation in step.invocations}

    try:
        while remaining:
            progressed = False
            for step in pipeline.steps:
                for invocation in step.invocations:
                    key = (step.step_id, invocation.invocation_id)
                    if key not in remaining:
                        continue
                    incoming_edges = [edge for edge in pipeline.edges if edge.to_endpoint.startswith(f"{step.step_id}.{invocation.invocation_id}.")]
                    if not _all_sources_ready(incoming_edges, pipeline_input_artifacts, produced_artifacts):
                        continue
                    service = service_index[invocation.service_id]
                    prepared_inputs = _prepare_invocation_inputs(
                        run_paths=run_paths,
                        step_id=step.step_id,
                        invocation=invocation,
                        service_inputs={port.name: port for port in service.contract.inputs},
                        incoming_edges=incoming_edges,
                        pipeline_input_artifacts=pipeline_input_artifacts,
                        produced_artifacts=produced_artifacts,
                    )
                    try:
                        runner_request = ServiceRunnerRequest(
                            step_id=step.step_id,
                            invocation_id=invocation.invocation_id,
                            service_id=invocation.service_id,
                            inputs=prepared_inputs,
                            input_contracts={port.name: port for port in service.contract.inputs},
                            output_contracts={port.name: port for port in service.contract.outputs},
                            output_root=run_paths.invocation_outputs_dir(step.step_id, invocation.invocation_id),
                            config=invocation.config,
                            log_path=run_paths.invocation_log_file(step.step_id, invocation.invocation_id),
                        )
                        runner_result = request.service_runner.run(runner_request)
                        if request.validate_outputs:
                            _validate_invocation_outputs(
                                outputs=runner_result.outputs,
                                output_contracts={port.name: port for port in service.contract.outputs},
                                registry_path=request.registry_path,
                            )
                    except Exception as error:
                        failed_manifest_path = _write_failed_invocation_manifest(
                            run_paths=run_paths,
                            step_id=step.step_id,
                            invocation_id=invocation.invocation_id,
                            service_id=invocation.service_id,
                            inputs=prepared_inputs,
                            error=error,
                        )
                        invocation_manifest_paths.append(failed_manifest_path)
                        raise
                    manifest = InvocationManifest(
                        step_id=step.step_id,
                        invocation_id=invocation.invocation_id,
                        service_id=invocation.service_id,
                        status="succeeded",
                        inputs={name: tuple(str(path) for path in paths) for name, paths in prepared_inputs.items()},
                        outputs={name: tuple(str(path) for path in paths) for name, paths in runner_result.outputs.items()},
                        exit_code=runner_result.exit_code,
                        log_path=str(run_paths.invocation_log_file(step.step_id, invocation.invocation_id)),
                    )
                    manifest_path = run_paths.invocation_manifest_file(step.step_id, invocation.invocation_id)
                    write_invocation_manifest(manifest_path, manifest)
                    invocation_manifest_paths.append(manifest_path)
                    for port_name, paths in runner_result.outputs.items():
                        produced_artifacts[f"{step.step_id}.{invocation.invocation_id}.{port_name}"] = paths
                    del remaining[key]
                    progressed = True
            if not progressed:
                unresolved = ", ".join(f"{step_id}.{invocation_id}" for step_id, invocation_id in remaining)
                raise ConfigurationError(f"Pipeline execution could not progress. Remaining invocations: {unresolved}")

        pipeline_outputs = _materialize_pipeline_outputs(run_paths, pipeline, pipeline_input_artifacts, produced_artifacts)
        run_manifest = RunManifest(
            pipeline_id=pipeline.pipeline_id,
            run_id=run_paths.run_id,
            status="succeeded",
            invocation_manifests=tuple(str(path) for path in invocation_manifest_paths),
            outputs={name: tuple(str(path) for path in paths) for name, paths in pipeline_outputs.items()},
        )
        write_run_manifest(run_paths.run_manifest_file, run_manifest)
        return PipelineRunResult(
            run_paths=run_paths,
            pipeline=pipeline,
            outputs=pipeline_outputs,
            invocation_manifests=tuple(invocation_manifest_paths),
        )
    except Exception as error:
        failed_run_manifest = RunManifest(
            pipeline_id=pipeline.pipeline_id,
            run_id=run_paths.run_id,
            status="failed",
            invocation_manifests=tuple(str(path) for path in invocation_manifest_paths),
            outputs={},
            error=str(error),
        )
        write_run_manifest(run_paths.run_manifest_file, failed_run_manifest)
        raise


def _materialize_pipeline_inputs(
    run_paths: RunPaths,
    pipeline: EnginePipelineDefinition,
    provided_inputs: Mapping[str, Path | tuple[Path, ...]],
) -> dict[str, tuple[Path, ...]]:
    materialized: dict[str, tuple[Path, ...]] = {}
    for port in pipeline.inputs:
        raw_value = provided_inputs.get(port.name)
        if raw_value is None:
            raise ConfigurationError(f"Missing pipeline input '{port.name}'.")
        source_paths = raw_value if isinstance(raw_value, tuple) else (raw_value,)
        if port.cardinality == "one" and len(source_paths) != 1:
            raise ConfigurationError(f"Pipeline input '{port.name}' expects one source artifact.")
        if len(source_paths) == 0:
            raise ConfigurationError(f"Pipeline input '{port.name}' requires at least one source artifact.")
        _validate_pipeline_input_modes(port_name=port.name, expected_mode=port.mode, source_paths=source_paths)
        target_root = run_paths.inputs_dir / port.name
        target_root.mkdir(parents=True, exist_ok=True)
        copied = tuple(_copy_input_path(source_path, target_root) for source_path in source_paths)
        materialized[f"pipeline:input.{port.name}"] = copied
    return materialized


def _validate_pipeline_input_modes(*, port_name: str, expected_mode: str, source_paths: tuple[Path, ...]) -> None:
    if expected_mode == "file":
        if any(not source_path.is_file() for source_path in source_paths):
            raise ConfigurationError(f"Pipeline input '{port_name}' expects file artifacts.")
        return
    if expected_mode == "directory":
        if any(not source_path.is_dir() for source_path in source_paths):
            raise ConfigurationError(f"Pipeline input '{port_name}' expects directory artifacts.")
        return
    raise ConfigurationError(f"Engine does not yet support pipeline input mode '{expected_mode}'.")


def _copy_input_path(source_path: Path, target_root: Path) -> Path:
    if source_path.is_file():
        target_path = target_root / source_path.name
        shutil.copy2(source_path, target_path)
        return target_path
    if source_path.is_dir():
        target_path = target_root / source_path.name
        if target_path.exists():
            shutil.rmtree(target_path)
        shutil.copytree(source_path, target_path)
        return target_path
    raise ConfigurationError(f"Input path does not exist: {source_path}")


def _all_sources_ready(
    incoming_edges,
    pipeline_input_artifacts: Mapping[str, tuple[Path, ...]],
    produced_artifacts: Mapping[str, tuple[Path, ...]],
) -> bool:
    for edge in incoming_edges:
        if edge.from_endpoint.startswith("pipeline:input."):
            if edge.from_endpoint not in pipeline_input_artifacts:
                return False
        elif edge.from_endpoint not in produced_artifacts:
            return False
    return True


def _prepare_invocation_inputs(
    *,
    run_paths: RunPaths,
    step_id: str,
    invocation: InvocationDefinition,
    service_inputs: Mapping[str, PortContract],
    incoming_edges,
    pipeline_input_artifacts: Mapping[str, tuple[Path, ...]],
    produced_artifacts: Mapping[str, tuple[Path, ...]],
) -> dict[str, tuple[Path, ...]]:
    prepared: dict[str, tuple[Path, ...]] = {}
    inputs_root = run_paths.invocation_inputs_dir(step_id, invocation.invocation_id)
    inputs_root.mkdir(parents=True, exist_ok=True)
    grouped_sources: dict[str, list[Path]] = {}
    for edge in incoming_edges:
        target_port = edge.to_endpoint.split(".")[-1]
        sources = pipeline_input_artifacts.get(edge.from_endpoint) or produced_artifacts.get(edge.from_endpoint)
        if sources is None:
            raise ConfigurationError(f"Missing resolved source artifacts for '{edge.from_endpoint}'.")
        grouped_sources.setdefault(target_port, []).extend(sources)

    for port_name, sources in grouped_sources.items():
        contract = service_inputs[port_name]
        port_root = inputs_root / port_name
        port_root.mkdir(parents=True, exist_ok=True)
        if contract.mode == "file":
            if contract.cardinality == "one" and len(sources) != 1:
                raise ConfigurationError(f"Service input port '{port_name}' expects one source artifact.")
            if contract.cardinality == "many":
                _validate_unique_filenames(sources, port_name)
            copied = tuple(_copy_input_path(source, port_root) for source in sources)
        elif contract.mode == "directory":
            merged_root = port_root / "merged"
            merged_root.mkdir(parents=True, exist_ok=True)
            _copy_directory_sources_with_collision_detection(sources, merged_root, port_name)
            copied = (merged_root,)
        else:
            raise ConfigurationError(f"Engine does not yet support input mode '{contract.mode}' for invocation prep.")
        prepared[port_name] = copied
    return prepared


def _materialize_pipeline_outputs(
    run_paths: RunPaths,
    pipeline: EnginePipelineDefinition,
    pipeline_inputs: Mapping[str, tuple[Path, ...]],
    produced_artifacts: Mapping[str, tuple[Path, ...]],
) -> dict[str, tuple[Path, ...]]:
    outputs: dict[str, tuple[Path, ...]] = {}
    output_edges = [edge for edge in pipeline.edges if edge.to_endpoint.startswith("pipeline:output.")]
    pipeline_output_contracts = {port.name: port for port in pipeline.outputs}
    for edge in output_edges:
        port_name = edge.to_endpoint.split(".", 1)[1]
        sources = pipeline_inputs.get(edge.from_endpoint) or produced_artifacts.get(edge.from_endpoint)
        if sources is None:
            raise ConfigurationError(f"Missing source artifacts for pipeline output '{edge.to_endpoint}'.")
        target_root = run_paths.outputs_dir / port_name
        target_root.mkdir(parents=True, exist_ok=True)
        copied = tuple(_copy_output_path(source, target_root) for source in sources)
        contract = pipeline_output_contracts[port_name]
        if contract.cardinality == "one" and len(copied) != 1:
            raise ConfigurationError(f"Pipeline output '{port_name}' expects one artifact.")
        outputs[port_name] = copied
    return outputs


def _copy_output_path(source: Path, target_root: Path) -> Path:
    if source.is_file():
        target_path = target_root / source.name
        shutil.copy2(source, target_path)
        return target_path
    if source.is_dir():
        target_path = target_root / source.name
        if target_path.exists():
            shutil.rmtree(target_path)
        shutil.copytree(source, target_path)
        return target_path
    raise ConfigurationError(f"Output source path does not exist: {source}")


def _validate_unique_filenames(sources: list[Path], port_name: str) -> None:
    seen: dict[str, Path] = {}
    for source in sources:
        existing = seen.get(source.name)
        if existing is not None:
            raise ConfigurationError(
                f"Filename collision for service input port '{port_name}': '{source.name}' from '{existing}' and '{source}'."
            )
        seen[source.name] = source


def _copy_directory_sources_with_collision_detection(sources: list[Path], merged_root: Path, port_name: str) -> None:
    seen: dict[Path, Path] = {}
    for source in sources:
        if source.is_dir():
            for child in source.rglob("*"):
                if child.is_dir():
                    continue
                relative = child.relative_to(source)
                _copy_directory_child_with_collision_detection(
                    child=child,
                    relative=relative,
                    merged_root=merged_root,
                    port_name=port_name,
                    seen=seen,
                )
        else:
            _copy_directory_child_with_collision_detection(
                child=source,
                relative=Path(source.name),
                merged_root=merged_root,
                port_name=port_name,
                seen=seen,
            )


def _copy_directory_child_with_collision_detection(
    *,
    child: Path,
    relative: Path,
    merged_root: Path,
    port_name: str,
    seen: dict[Path, Path],
) -> None:
    existing = seen.get(relative)
    if existing is not None:
        raise ConfigurationError(
            f"Relative path collision for service input port '{port_name}': '{relative.as_posix()}' from '{existing}' and '{child}'."
        )
    target = merged_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(child, target)
    seen[relative] = child


def _validate_invocation_outputs(
    *,
    outputs: Mapping[str, tuple[Path, ...]],
    output_contracts: Mapping[str, PortContract],
    registry_path: Path,
) -> None:
    validator = SchemaValidator()
    for port_name, contract in output_contracts.items():
        if contract.schema_ref is None:
            continue
        if contract.mode != "file":
            raise ConfigurationError(
                f"Schema validation is only supported for file outputs. Port '{port_name}' uses mode '{contract.mode}'."
            )
        resolved_schema_ref = str(_resolve_schema_path(contract.schema_ref, registry_path))
        artifact_paths = outputs.get(port_name, tuple())
        for artifact_path in artifact_paths:
            payload = _load_json_payload(artifact_path)
            validator.validate(payload, resolved_schema_ref)


def _load_json_payload(path: Path) -> object:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as error:
        raise MalformedJsonError(path, str(error)) from error


def _resolve_schema_path(schema_ref: str, registry_path: Path) -> Path:
    candidate = Path(schema_ref)
    if candidate.is_absolute():
        return candidate.resolve()

    repo_root = Path(__file__).resolve().parents[2]
    candidate_roots = (
        registry_path.parent,
        registry_path.parent.parent,
        repo_root,
    )
    for root in candidate_roots:
        resolved = (root / schema_ref).resolve()
        if resolved.exists():
            return resolved
    raise ConfigurationError(f"Could not resolve schemaRef '{schema_ref}' for invocation output validation.")


def _write_failed_invocation_manifest(
    *,
    run_paths: RunPaths,
    step_id: str,
    invocation_id: str,
    service_id: str,
    inputs: Mapping[str, tuple[Path, ...]],
    error: Exception,
) -> Path:
    manifest = InvocationManifest(
        step_id=step_id,
        invocation_id=invocation_id,
        service_id=service_id,
        status="failed",
        inputs={name: tuple(str(path) for path in paths) for name, paths in inputs.items()},
        outputs={},
        log_path=str(run_paths.invocation_log_file(step_id, invocation_id)),
        error=str(error),
    )
    manifest_path = run_paths.invocation_manifest_file(step_id, invocation_id)
    write_invocation_manifest(manifest_path, manifest)
    return manifest_path
