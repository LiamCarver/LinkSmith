from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from linksmith_core.models import JsonValue, PortContract, ServiceContract


@dataclass(frozen=True)
class EngineRegisteredService:
    service_id: str
    kind: str
    deterministic: bool
    description: str
    entrypoint: str
    contract: ServiceContract
    config_schema: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class EngineRegistryDocument:
    services: tuple[EngineRegisteredService, ...]


@dataclass(frozen=True)
class DockerRuntimeServiceDefinition:
    image: str
    input_arguments: dict[str, str]
    output_dir_argument: str
    environment: dict[str, str] = field(default_factory=dict)
    output_file_name_arguments: dict[str, str] = field(default_factory=dict)
    output_file_names: dict[str, str] = field(default_factory=dict)
    schema_base_dir_argument: str | None = None
    schema_base_dir_value: str | None = None
    input_mount_root: str = "/workspace/inputs"
    output_mount_root: str = "/workspace/outputs"
    extra_args: tuple[str, ...] = tuple()


@dataclass(frozen=True)
class EngineRuntimeConfig:
    runner_kind: Literal["docker"]
    docker_services: dict[str, DockerRuntimeServiceDefinition]


@dataclass(frozen=True)
class ServicePortRef:
    service_port: str
    alias: str | None = None


@dataclass(frozen=True)
class InvocationDefinition:
    invocation_id: str
    service_id: str
    description: str | None = None
    config: dict[str, JsonValue] = field(default_factory=dict)
    inputs: tuple[ServicePortRef, ...] = tuple()
    outputs: tuple[ServicePortRef, ...] = tuple()


@dataclass(frozen=True)
class StepDefinition:
    step_id: str
    description: str | None
    invocations: tuple[InvocationDefinition, ...]


@dataclass(frozen=True)
class PipelineEdge:
    from_endpoint: str
    to_endpoint: str
    label: str | None = None


@dataclass(frozen=True)
class EnginePipelineDefinition:
    pipeline_id: str
    name: str | None
    description: str | None
    version: str | None
    inputs: tuple[PortContract, ...]
    outputs: tuple[PortContract, ...]
    steps: tuple[StepDefinition, ...]
    edges: tuple[PipelineEdge, ...]


@dataclass(frozen=True)
class EndpointReference:
    kind: Literal["pipeline_input", "pipeline_output", "invocation"]
    port_name: str
    step_id: str | None = None
    invocation_id: str | None = None


@dataclass(frozen=True)
class RunPaths:
    run_id: str
    root: Path
    pipeline_dir: Path
    inputs_dir: Path
    invocation_artifacts_dir: Path
    manifests_dir: Path
    invocation_manifests_dir: Path
    logs_dir: Path
    invocation_logs_dir: Path
    outputs_dir: Path
    pipeline_file: Path
    registry_file: Path
    run_manifest_file: Path
    engine_log_file: Path

    def invocation_root(self, step_id: str, invocation_id: str) -> Path:
        return self.invocation_artifacts_dir / step_id / invocation_id

    def invocation_inputs_dir(self, step_id: str, invocation_id: str) -> Path:
        return self.invocation_root(step_id, invocation_id) / "inputs"

    def invocation_outputs_dir(self, step_id: str, invocation_id: str) -> Path:
        return self.invocation_root(step_id, invocation_id) / "outputs"

    def invocation_manifest_file(self, step_id: str, invocation_id: str) -> Path:
        return self.invocation_manifests_dir / f"{step_id}.{invocation_id}.json"

    def invocation_log_file(self, step_id: str, invocation_id: str) -> Path:
        return self.invocation_logs_dir / f"{step_id}.{invocation_id}.log"


@dataclass(frozen=True)
class InvocationManifest:
    step_id: str
    invocation_id: str
    service_id: str
    status: Literal["pending", "succeeded", "failed"]
    inputs: dict[str, tuple[str, ...]]
    outputs: dict[str, tuple[str, ...]]
    exit_code: int | None = None
    log_path: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class RunManifest:
    pipeline_id: str
    run_id: str
    status: Literal["succeeded", "failed"]
    invocation_manifests: tuple[str, ...]
    outputs: dict[str, tuple[str, ...]]
    error: str | None = None
