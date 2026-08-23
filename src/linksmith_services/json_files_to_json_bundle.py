from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any

from linksmith_core.errors import ConfigurationError
from linksmith_core.models import JsonArtifact, JsonOutput, JsonValue, PortContract, ServiceContract, ServiceRunRequest
from linksmith_core.runtime import run_service

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SourceJsonDocument:
    relative_path: PurePath
    data: JsonValue


def bundle_json_documents(documents: list[SourceJsonDocument]) -> dict[str, Any]:
    if not documents:
        raise ConfigurationError("JSON bundle service requires at least one input document.")

    normalized = sorted(documents, key=lambda item: item.relative_path.as_posix())
    seen_paths: set[str] = set()
    items: list[dict[str, Any]] = []
    source_refs: list[dict[str, str]] = []

    for index, document in enumerate(normalized, start=1):
        relative_path = document.relative_path.as_posix()
        if relative_path in seen_paths:
            raise ConfigurationError(f"Duplicate bundle input relative path '{relative_path}'.")
        seen_paths.add(relative_path)
        if not isinstance(document.data, (dict, list)):
            raise ConfigurationError(
                f"Bundle input '{relative_path}' must have a JSON object or array root."
            )
        file_name = document.relative_path.name
        source_id = _build_source_id(index, document.relative_path)
        items.append(
            {
                "sourceId": source_id,
                "fileName": file_name,
                "relativePath": relative_path,
                "data": document.data,
            }
        )
        source_refs.append(
            {
                "sourceId": source_id,
                "relativePath": relative_path,
            }
        )

    return {
        "artifactType": "json-bundle",
        "items": items,
        "sourceRefs": source_refs,
    }


class JsonFilesToJsonBundleService:
    contract = ServiceContract(
        service_id="json-files-to-json-bundle",
        inputs=(
            PortContract(
                name="documents",
                type="json-document",
                mode="file",
                cardinality="many",
            ),
        ),
        outputs=(
            PortContract(
                name="bundle",
                type="json-bundle",
                mode="file",
                cardinality="one",
                schema_ref="schemas/json-bundle.schema.json",
            ),
        ),
        version="0.1.0",
    )

    def __init__(
        self,
        *,
        documents_root: Path | None = None,
        output_file_name: str = "bundle.json",
    ) -> None:
        self._documents_root = documents_root.resolve() if documents_root is not None else None
        self._output_file_name = output_file_name

    def execute(self, inputs, context):
        documents: list[SourceJsonDocument] = []
        for artifact in inputs["documents"]:
            if not isinstance(artifact, JsonArtifact):
                raise ConfigurationError("Bundle input documents must be loaded as JSON artifacts.")
            relative_path = _resolve_relative_path(artifact.path, self._documents_root)
            documents.append(
                SourceJsonDocument(
                    relative_path=relative_path,
                    data=artifact.data,
                )
            )
        payload = bundle_json_documents(documents)
        return {
            "bundle": JsonOutput(
                relative_path=PurePath(self._output_file_name),
                data=payload,
            )
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bundle multiple JSON files into one deterministic JSON context artifact."
    )
    parser.add_argument(
        "--documents-dir",
        required=True,
        help="Directory containing the JSON document inputs for the many-file documents port.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the bundle output port folder should be written.",
    )
    parser.add_argument(
        "--output-file-name",
        default="bundle.json",
        help="Output JSON filename relative to the bundle port directory.",
    )
    parser.add_argument(
        "--schema-base-dir",
        default=".",
        help="Base directory used to resolve schemaRef values.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    documents_dir = Path(args.documents_dir)
    service = JsonFilesToJsonBundleService(
        documents_root=documents_dir,
        output_file_name=args.output_file_name,
    )
    request = ServiceRunRequest(
        inputs={"documents": _collect_document_paths(documents_dir)},
        output_root=Path(args.output_dir),
        schema_base_dir=Path(args.schema_base_dir),
    )
    result = run_service(service, request)
    for port_name, paths in result.written_outputs.items():
        for path in paths:
            print(f"{port_name}: {path}")
    return 0


def _collect_document_paths(documents_dir: Path) -> tuple[Path, ...]:
    if not documents_dir.exists() or not documents_dir.is_dir():
        raise ConfigurationError(f"Documents directory does not exist: {documents_dir}")
    paths = tuple(sorted(path for path in documents_dir.rglob("*") if path.is_file()))
    if not paths:
        raise ConfigurationError(f"Documents directory does not contain any files: {documents_dir}")
    return paths


def _resolve_relative_path(path: Path, root: Path | None) -> PurePath:
    if root is not None:
        try:
            return PurePath(path.resolve().relative_to(root))
        except ValueError:
            pass
    return PurePath(path.name)


def _build_source_id(index: int, relative_path: PurePath) -> str:
    stem = Path(relative_path.name).stem.lower()
    slug = _SLUG_PATTERN.sub("-", stem).strip("-")
    if not slug:
        slug = "document"
    return f"{index:03d}-{slug}"


if __name__ == "__main__":
    raise SystemExit(main())
