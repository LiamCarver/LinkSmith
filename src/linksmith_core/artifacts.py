from __future__ import annotations

import json
from pathlib import Path, PurePath
from typing import Iterable

from .errors import (
    ConfigurationError,
    MalformedJsonError,
    MissingArtifactError,
    OutputWriteError,
    UnsupportedArtifactModeError,
)
from .models import (
    ArtifactReference,
    DirectoryEntry,
    JsonArtifact,
    JsonOutput,
    LoadedArtifact,
    MarkdownArtifact,
    MarkdownDirectoryArtifact,
    MarkdownDirectoryOutput,
    MarkdownOutput,
    PortContract,
    ProducedArtifact,
)


def output_matches_port_contract(port: PortContract, output: ProducedArtifact) -> bool:
    if port.mode == "directory":
        return (
            isinstance(output, MarkdownDirectoryOutput)
            and _infer_artifact_kind(
                artifact_type=port.type,
                schema_ref=port.schema_ref,
            )
            == "markdown"
        )
    artifact_kind = _infer_artifact_kind(
        artifact_type=port.type,
        schema_ref=port.schema_ref,
        output=output,
    )
    if artifact_kind == "json":
        return isinstance(output, JsonOutput)
    if artifact_kind == "markdown":
        return isinstance(output, MarkdownOutput)
    return False


def load_port_inputs(port: PortContract, provided: Path | tuple[Path, ...]) -> tuple[LoadedArtifact, ...]:
    paths = _normalize_paths(provided)
    if port.cardinality == "one" and len(paths) != 1:
        raise ConfigurationError(
            f"Port '{port.name}' expects exactly one artifact, received {len(paths)}."
        )
    if port.cardinality == "many" and not paths:
        raise ConfigurationError(f"Port '{port.name}' expects at least one artifact.")
    return tuple(_load_single_artifact(port, path) for path in paths)


def write_port_outputs(
    port: PortContract,
    outputs: ProducedArtifact | tuple[ProducedArtifact, ...],
    output_root: Path,
) -> tuple[Path, ...]:
    normalized = outputs if isinstance(outputs, tuple) else (outputs,)
    if port.mode == "artifact-ref":
        raise UnsupportedArtifactModeError(
            f"Output port '{port.name}' uses unsupported mode '{port.mode}'."
        )
    if port.mode == "directory":
        if len(normalized) != 1 or not isinstance(normalized[0], MarkdownDirectoryOutput):
            raise ConfigurationError(
                f"Directory output port '{port.name}' expects one MarkdownDirectoryOutput."
            )
        return _write_markdown_directory(normalized[0], output_root)
    if port.cardinality == "one" and len(normalized) != 1:
        raise ConfigurationError(
            f"Output port '{port.name}' expects exactly one artifact, received {len(normalized)}."
        )
    return tuple(_write_single_output(item, output_root) for item in normalized)


def _load_single_artifact(port: PortContract, path: Path) -> LoadedArtifact:
    if not path.exists():
        raise MissingArtifactError(path)
    if port.mode == "artifact-ref":
        return ArtifactReference(path=path, artifact_type=port.type, mode=port.mode)
    if port.mode == "directory":
        return _load_markdown_directory(port, path)
    if port.mode != "file":
        raise UnsupportedArtifactModeError(
            f"Port '{port.name}' uses unsupported mode '{port.mode}'."
        )
    artifact_kind = _infer_artifact_kind(
        artifact_type=port.type,
        schema_ref=port.schema_ref,
        path=path,
    )
    if artifact_kind == "json":
        return _load_json_artifact(port, path)
    if artifact_kind == "markdown":
        return _load_markdown_artifact(port, path)
    raise UnsupportedArtifactModeError(
        f"Port '{port.name}' uses unsupported artifact type '{port.type}'."
    )


def _load_json_artifact(port: PortContract, path: Path) -> JsonArtifact:
    if not path.is_file():
        raise ConfigurationError(f"JSON input for port '{port.name}' must be a file: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise MalformedJsonError(path, str(exc)) from exc
    return JsonArtifact(path=path, artifact_type=port.type, mode=port.mode, data=payload)


def _load_markdown_artifact(port: PortContract, path: Path) -> MarkdownArtifact:
    if not path.is_file():
        raise ConfigurationError(
            f"Markdown input for port '{port.name}' must be a file: {path}"
        )
    with path.open("r", encoding="utf-8") as handle:
        text = handle.read()
    return MarkdownArtifact(path=path, artifact_type=port.type, mode=port.mode, text=text)


def _load_markdown_directory(port: PortContract, path: Path) -> MarkdownDirectoryArtifact:
    if not path.is_dir():
        raise ConfigurationError(
            f"Directory input for port '{port.name}' must be a directory: {path}"
        )
    if (
        _infer_artifact_kind(
            artifact_type=port.type,
            schema_ref=port.schema_ref,
            path=path,
        )
        != "markdown"
    ):
        raise UnsupportedArtifactModeError(
            f"Directory input for port '{port.name}' only supports Markdown in v1."
        )
    documents = tuple(_read_markdown_directory(path))
    return MarkdownDirectoryArtifact(
        path=path,
        artifact_type=port.type,
        mode=port.mode,
        documents=documents,
    )


def _read_markdown_directory(path: Path) -> Iterable[DirectoryEntry]:
    for file_path in sorted(path.rglob("*.md")):
        if not file_path.is_file():
            continue
        with file_path.open("r", encoding="utf-8") as handle:
            yield DirectoryEntry(
                relative_path=file_path.relative_to(path),
                source_path=file_path,
                text=handle.read(),
            )


def _write_single_output(output: ProducedArtifact, output_root: Path) -> Path:
    if isinstance(output, JsonOutput):
        target = output_root / Path(output.relative_path)
        _ensure_parent(target)
        with target.open("w", encoding="utf-8") as handle:
            json.dump(output.data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        return target
    if isinstance(output, MarkdownOutput):
        target = output_root / Path(output.relative_path)
        _ensure_parent(target)
        with target.open("w", encoding="utf-8") as handle:
            handle.write(output.text)
        return target
    if isinstance(output, MarkdownDirectoryOutput):
        raise ConfigurationError("Directory outputs must be written through a directory port.")
    raise OutputWriteError(f"Unsupported output artifact: {type(output).__name__}")


def _write_markdown_directory(output: MarkdownDirectoryOutput, output_root: Path) -> tuple[Path, ...]:
    root = output_root / Path(output.relative_path)
    written: list[Path] = []
    for document in output.documents:
        target = root / Path(document.relative_path)
        _ensure_parent(target)
        with target.open("w", encoding="utf-8") as handle:
            handle.write(document.text)
        written.append(target)
    return tuple(written)


def _normalize_paths(provided: Path | tuple[Path, ...]) -> tuple[Path, ...]:
    if isinstance(provided, tuple):
        return provided
    return (provided,)


def _infer_artifact_kind(
    artifact_type: str,
    schema_ref: str | None = None,
    path: Path | None = None,
    output: ProducedArtifact | None = None,
) -> str:
    normalized = artifact_type.strip().lower()
    if normalized in {"json", "application/json"} or normalized.endswith("+json"):
        return "json"
    if normalized in {"mustache-template", "template/mustache"}:
        return "markdown"
    if normalized in {"markdown", "md", "text/markdown"}:
        return "markdown"
    if "markdown" in normalized:
        return "markdown"
    if schema_ref is not None and schema_ref.strip().lower().endswith(".json"):
        return "json"
    if path is not None and path.suffix.lower() in {".json", ".canvas"}:
        return "json"
    if path is not None and path.suffix.lower() in {".md", ".markdown", ".mustache"}:
        return "markdown"
    if isinstance(output, JsonOutput):
        return "json"
    if isinstance(output, (MarkdownOutput, MarkdownDirectoryOutput)):
        return "markdown"
    raise UnsupportedArtifactModeError(f"Unsupported artifact type '{artifact_type}'.")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_dir():
        raise OutputWriteError(f"Cannot write file output over directory: {path}")
