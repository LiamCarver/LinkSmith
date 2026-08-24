from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any

from linksmith_core.errors import ConfigurationError
from linksmith_core.models import (
    JsonOutput,
    MarkdownDirectoryArtifact,
    PortContract,
    ServiceContract,
    ServiceRunRequest,
)
from linksmith_core.runtime import run_service

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SourceMarkdownDocument:
    relative_path: PurePath
    text: str


def build_markdown_corpus(documents: list[SourceMarkdownDocument]) -> dict[str, Any]:
    if not documents:
        raise ConfigurationError("Markdown corpus service requires at least one input document.")

    normalized = sorted(documents, key=lambda item: item.relative_path.as_posix())
    seen_paths: set[str] = set()
    items: list[dict[str, str]] = []
    source_refs: list[dict[str, str]] = []

    for index, document in enumerate(normalized, start=1):
        relative_path = document.relative_path.as_posix()
        if relative_path in seen_paths:
            raise ConfigurationError(f"Duplicate corpus input relative path '{relative_path}'.")
        seen_paths.add(relative_path)
        if not document.text.strip():
            raise ConfigurationError(f"Corpus input '{relative_path}' must not be empty.")
        source_id = _build_source_id(index, document.relative_path)
        items.append(
            {
                "sourceId": source_id,
                "fileName": document.relative_path.name,
                "relativePath": relative_path,
                "content": document.text,
            }
        )
        source_refs.append(
            {
                "sourceId": source_id,
                "relativePath": relative_path,
            }
        )

    return {
        "artifactType": "markdown-corpus",
        "items": items,
        "sourceRefs": source_refs,
    }


class MarkdownDirectoryToJsonCorpusService:
    contract = ServiceContract(
        service_id="markdown-directory-to-json-corpus",
        inputs=(
            PortContract(
                name="documents",
                type="markdown-directory",
                mode="directory",
                cardinality="one",
            ),
        ),
        outputs=(
            PortContract(
                name="corpus",
                type="markdown-corpus",
                mode="file",
                cardinality="one",
                schema_ref="schemas/markdown-corpus.schema.json",
            ),
        ),
        version="0.1.0",
    )

    def __init__(self, output_file_name: str = "corpus.json") -> None:
        self._output_file_name = output_file_name

    def execute(self, inputs, context):
        artifact = inputs["documents"][0]
        if not isinstance(artifact, MarkdownDirectoryArtifact):
            raise ConfigurationError("Corpus input documents must be loaded as a Markdown directory artifact.")
        documents = [
            SourceMarkdownDocument(
                relative_path=entry.relative_path,
                text=entry.text,
            )
            for entry in artifact.documents
        ]
        payload = build_markdown_corpus(documents)
        return {
            "corpus": JsonOutput(
                relative_path=PurePath(self._output_file_name),
                data=payload,
            )
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read a Markdown directory recursively and emit one deterministic JSON corpus artifact."
    )
    parser.add_argument(
        "--documents-dir",
        required=True,
        help="Directory containing Markdown documents for the documents input port.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the corpus output port folder should be written.",
    )
    parser.add_argument(
        "--output-file-name",
        default="corpus.json",
        help="Output JSON filename relative to the corpus port directory.",
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
    service = MarkdownDirectoryToJsonCorpusService(output_file_name=args.output_file_name)
    request = ServiceRunRequest(
        inputs={"documents": documents_dir},
        output_root=Path(args.output_dir),
        schema_base_dir=Path(args.schema_base_dir),
    )
    result = run_service(service, request)
    for port_name, paths in result.written_outputs.items():
        for path in paths:
            print(f"{port_name}: {path}")
    return 0


def _build_source_id(index: int, relative_path: PurePath) -> str:
    stem = Path(relative_path.name).stem.lower()
    slug = _SLUG_PATTERN.sub("-", stem).strip("-")
    if not slug:
        slug = "document"
    return f"{index:03d}-{slug}"


if __name__ == "__main__":
    raise SystemExit(main())
