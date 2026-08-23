from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from shutil import which
from typing import Mapping, Protocol

from linksmith_core.models import JsonValue, PortContract

from .errors import ServiceRunnerError


@dataclass(frozen=True)
class ServiceRunnerRequest:
    step_id: str
    invocation_id: str
    service_id: str
    inputs: Mapping[str, tuple[Path, ...]]
    input_contracts: Mapping[str, PortContract]
    output_contracts: Mapping[str, PortContract]
    output_root: Path
    config: Mapping[str, JsonValue]
    log_path: Path


@dataclass(frozen=True)
class ServiceRunnerResult:
    outputs: Mapping[str, tuple[Path, ...]]
    exit_code: int


class ServiceRunner(Protocol):
    def run(self, request: ServiceRunnerRequest) -> ServiceRunnerResult:
        ...


@dataclass(frozen=True)
class DockerServiceConfig:
    image: str
    input_arguments: Mapping[str, str]
    output_dir_argument: str
    environment: Mapping[str, str] = field(default_factory=dict)
    output_file_name_arguments: Mapping[str, str] = field(default_factory=dict)
    output_file_names: Mapping[str, str] = field(default_factory=dict)
    schema_base_dir_argument: str | None = None
    schema_base_dir_value: str | None = None
    input_mount_root: str = "/workspace/inputs"
    output_mount_root: str = "/workspace/outputs"
    extra_args: tuple[str, ...] = tuple()


class DockerServiceRunner:
    def __init__(self, service_configs: Mapping[str, DockerServiceConfig]) -> None:
        self._service_configs = dict(service_configs)

    def run(self, request: ServiceRunnerRequest) -> ServiceRunnerResult:
        if which("docker") is None:
            raise ServiceRunnerError("Docker is not available in PATH.")
        service_config = self._service_configs.get(request.service_id)
        if service_config is None:
            raise ServiceRunnerError(f"No Docker runtime config is registered for service '{request.service_id}'.")

        command: list[str] = ["docker", "run", "--rm"]
        service_arguments: list[str] = []
        output_root_host = request.output_root.resolve()
        output_root_host.mkdir(parents=True, exist_ok=True)
        command.extend(["-v", f"{output_root_host}:{service_config.output_mount_root}"])
        for name, value in service_config.environment.items():
            command.extend(["-e", f"{name}={value}"])

        for port_name, port_contract in request.input_contracts.items():
            input_paths = request.inputs.get(port_name, tuple())
            if not input_paths:
                continue
            argument_name = service_config.input_arguments.get(port_name)
            if argument_name is None:
                raise ServiceRunnerError(
                    f"No input argument mapping is configured for service '{request.service_id}' port '{port_name}'."
                )
            if port_contract.mode == "file":
                if port_contract.cardinality == "many":
                    host_path = _resolve_many_file_input_root(request.service_id, port_name, input_paths)
                    container_path = f"{service_config.input_mount_root}/{port_name}"
                    command.extend(["-v", f"{host_path}:{container_path}:ro"])
                    service_arguments.extend([argument_name, container_path])
                else:
                    if len(input_paths) != 1:
                        raise ServiceRunnerError(
                            f"Docker runner currently expects one prepared file for input port '{port_name}'."
                        )
                    host_path = input_paths[0].resolve()
                    container_path = f"{service_config.input_mount_root}/{port_name}/{host_path.name}"
                    command.extend(["-v", f"{host_path}:{container_path}:ro"])
                    service_arguments.extend([argument_name, container_path])
            elif port_contract.mode == "directory":
                if len(input_paths) != 1:
                    raise ServiceRunnerError(
                        f"Docker runner currently expects one prepared directory for input port '{port_name}'."
                    )
                host_path = input_paths[0].resolve()
                container_path = f"{service_config.input_mount_root}/{port_name}"
                command.extend(["-v", f"{host_path}:{container_path}:ro"])
                service_arguments.extend([argument_name, container_path])
            else:
                raise ServiceRunnerError(
                    f"Docker runner does not support mode '{port_contract.mode}' for port '{port_name}'."
                )

        command.append(service_config.image)
        command.extend(service_config.extra_args)
        command.extend(service_arguments)
        command.extend([service_config.output_dir_argument, service_config.output_mount_root])
        for port_name, argument_name in service_config.output_file_name_arguments.items():
            filename = service_config.output_file_names.get(port_name)
            if filename is not None:
                command.extend([argument_name, filename])
        if service_config.schema_base_dir_argument and service_config.schema_base_dir_value:
            command.extend([service_config.schema_base_dir_argument, service_config.schema_base_dir_value])

        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        request.log_path.parent.mkdir(parents=True, exist_ok=True)
        request.log_path.write_text(completed.stdout, encoding="utf-8")
        if completed.returncode != 0:
            raise ServiceRunnerError(
                f"Service '{request.service_id}' exited with code {completed.returncode}."
            )

        output_paths: dict[str, tuple[Path, ...]] = {}
        for port_name, port_contract in request.output_contracts.items():
            port_root = output_root_host / port_name
            if port_contract.mode == "file":
                filename = service_config.output_file_names.get(port_name)
                if filename is None:
                    files = tuple(sorted(path for path in port_root.rglob("*") if path.is_file()))
                    output_paths[port_name] = files
                else:
                    output_paths[port_name] = (port_root / filename,)
            elif port_contract.mode == "directory":
                output_paths[port_name] = (port_root,)
            else:
                raise ServiceRunnerError(
                    f"Docker runner does not support output mode '{port_contract.mode}' for port '{port_name}'."
                )
        return ServiceRunnerResult(outputs=output_paths, exit_code=completed.returncode)


def _resolve_many_file_input_root(service_id: str, port_name: str, input_paths: tuple[Path, ...]) -> Path:
    parent_roots = {path.parent for path in input_paths}
    if len(parent_roots) != 1:
        raise ServiceRunnerError(
            f"Prepared many-file input port '{port_name}' for service '{service_id}' must share one directory."
        )
    return next(iter(parent_roots)).resolve()
