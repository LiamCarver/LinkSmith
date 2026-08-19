from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Literal, Mapping, TypeAlias

ArtifactMode: TypeAlias = Literal["file", "directory", "artifact-ref"]
ArtifactCardinality: TypeAlias = Literal["one", "many"]
JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True)
class PortContract:
    name: str
    type: str
    mode: ArtifactMode
    cardinality: ArtifactCardinality
    required: bool = True
    description: str | None = None
    schema_ref: str | None = None


@dataclass(frozen=True)
class ServiceContract:
    service_id: str
    inputs: tuple[PortContract, ...]
    outputs: tuple[PortContract, ...]
    version: str | None = None


@dataclass(frozen=True)
class ArtifactReference:
    path: Path
    artifact_type: str
    mode: ArtifactMode


@dataclass(frozen=True)
class JsonArtifact(ArtifactReference):
    data: JsonValue


@dataclass(frozen=True)
class MarkdownArtifact(ArtifactReference):
    text: str


@dataclass(frozen=True)
class DirectoryEntry:
    relative_path: PurePath
    source_path: Path
    text: str


@dataclass(frozen=True)
class MarkdownDirectoryArtifact(ArtifactReference):
    documents: tuple[DirectoryEntry, ...]


LoadedArtifact = JsonArtifact | MarkdownArtifact | MarkdownDirectoryArtifact | ArtifactReference
ArtifactType = LoadedArtifact


@dataclass(frozen=True)
class JsonOutput:
    relative_path: PurePath
    data: JsonValue


@dataclass(frozen=True)
class MarkdownOutput:
    relative_path: PurePath
    text: str


@dataclass(frozen=True)
class MarkdownDocument:
    relative_path: PurePath
    text: str


@dataclass(frozen=True)
class MarkdownDirectoryOutput:
    relative_path: PurePath
    documents: tuple[MarkdownDocument, ...]


ProducedArtifact = JsonOutput | MarkdownOutput | MarkdownDirectoryOutput


@dataclass(frozen=True)
class LogEntry:
    stage: str
    message: str
    details: Mapping[str, str] = field(default_factory=dict)


@dataclass
class ServiceContext:
    service_name: str
    working_directory: Path | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    logs: list[LogEntry] = field(default_factory=list)


@dataclass(frozen=True)
class ServiceRunRequest:
    inputs: Mapping[str, Path | tuple[Path, ...]]
    output_root: Path
    schema_base_dir: Path | None = None
    working_directory: Path | None = None


@dataclass(frozen=True)
class ServiceRunResult:
    service_name: str
    written_outputs: Mapping[str, tuple[Path, ...]]
    logs: tuple[LogEntry, ...]
