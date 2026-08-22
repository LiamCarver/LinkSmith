from __future__ import annotations

import argparse
import re
from pathlib import Path, PurePath
from typing import Any

import chevron

from linksmith_core.errors import ConfigurationError
from linksmith_core.models import JsonArtifact, MarkdownArtifact, MarkdownOutput, PortContract, ServiceContract, ServiceRunRequest
from linksmith_core.runtime import run_service

_TAG_PATTERN = re.compile(r"{{\s*([#/^!]?)\s*([^{}]+?)\s*}}")
_MISSING = object()


def render_markdown_document(payload: dict[str, Any], template: str) -> str:
    if not isinstance(payload, dict):
        raise ConfigurationError("Renderer data JSON root must be an object.")
    _validate_template_context(template, payload)
    rendered = chevron.render(template, payload)
    if not rendered.strip():
        raise ConfigurationError("Rendered Markdown output must not be empty.")
    return rendered


class JsonToMarkdownRendererService:
    contract = ServiceContract(
        service_id="json-to-markdown-renderer",
        inputs=(
            PortContract(
                name="data",
                type="json-document",
                mode="file",
                cardinality="one",
            ),
            PortContract(
                name="template",
                type="mustache-template",
                mode="file",
                cardinality="one",
            ),
        ),
        outputs=(
            PortContract(
                name="document",
                type="markdown-document",
                mode="file",
                cardinality="one",
            ),
        ),
        version="0.1.0",
    )

    def __init__(self, output_file_name: str = "document.md") -> None:
        self._output_file_name = output_file_name

    def execute(self, inputs, context):
        data_artifact = inputs["data"][0]
        template_artifact = inputs["template"][0]
        if not isinstance(data_artifact, JsonArtifact):
            raise ConfigurationError("Renderer data input must be loaded as a JSON artifact.")
        if not isinstance(template_artifact, MarkdownArtifact):
            raise ConfigurationError("Renderer template input must be loaded as a text artifact.")
        if not isinstance(data_artifact.data, dict):
            raise ConfigurationError("Renderer data JSON root must be an object.")
        rendered = render_markdown_document(data_artifact.data, template_artifact.text)
        return {
            "document": MarkdownOutput(
                relative_path=PurePath(self._output_file_name),
                text=rendered,
            )
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render Markdown from JSON and a Mustache template."
    )
    parser.add_argument("--data", required=True, help="Path to the JSON data input file.")
    parser.add_argument("--template", required=True, help="Path to the Mustache template input file.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the document output port folder should be written.",
    )
    parser.add_argument(
        "--output-file-name",
        default="document.md",
        help="Output Markdown filename relative to the document port directory.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    service = JsonToMarkdownRendererService(output_file_name=args.output_file_name)
    request = ServiceRunRequest(
        inputs={
            "data": Path(args.data),
            "template": Path(args.template),
        },
        output_root=Path(args.output_dir),
    )
    result = run_service(service, request)
    for port_name, paths in result.written_outputs.items():
        for path in paths:
            print(f"{port_name}: {path}")
    return 0


def _validate_template_context(template: str, payload: dict[str, Any]) -> None:
    _validate_block(template, (payload,))


def _validate_block(template: str, contexts: tuple[Any, ...]) -> None:
    position = 0
    while True:
        match = _TAG_PATTERN.search(template, position)
        if match is None:
            return
        tag_type = match.group(1)
        tag_name = match.group(2).strip()
        position = match.end()

        if tag_type == "":
            _resolve_context_value(tag_name, contexts)
            continue
        if tag_type == "!":
            continue
        if tag_type == "^":
            section_start = match.end()
            section_end, inner_template = _extract_section(template, section_start, tag_name)
            section_value = _resolve_context_value(tag_name, contexts, allow_missing=True)
            if _should_render_inverted_section(section_value):
                _validate_block(inner_template, contexts)
            position = section_end
            continue
        if tag_type == "#":
            section_start = match.end()
            section_end, inner_template = _extract_section(template, section_start, tag_name)
            section_value = _resolve_context_value(tag_name, contexts, allow_missing=True)
            for child_contexts in _iter_section_contexts(section_value, contexts):
                _validate_block(inner_template, child_contexts)
            position = section_end
            continue
        if tag_type == "/":
            continue


def _extract_section(template: str, start: int, tag_name: str) -> tuple[int, str]:
    depth = 1
    position = start
    while True:
        match = _TAG_PATTERN.search(template, position)
        if match is None:
            raise ConfigurationError(f"Template section '{tag_name}' is not closed.")
        inner_type = match.group(1)
        inner_name = match.group(2).strip()
        if inner_name == tag_name:
            if inner_type == "#":
                depth += 1
            elif inner_type == "/":
                depth -= 1
                if depth == 0:
                    return match.end(), template[start:match.start()]
        position = match.end()


def _iter_section_contexts(value: Any, contexts: tuple[Any, ...]) -> tuple[tuple[Any, ...], ...]:
    if value is _MISSING or value is False or value is None:
        return tuple()
    if isinstance(value, list):
        return tuple((item, *contexts) for item in value)
    if value == "":
        return tuple()
    return ((value, *contexts),)


def _resolve_context_value(path: str, contexts: tuple[Any, ...], *, allow_missing: bool = False) -> Any:
    if path == ".":
        return contexts[0]
    for context in contexts:
        resolved = _resolve_from_context(path, context, allow_missing=True)
        if resolved is not _MISSING:
            return resolved
    if allow_missing:
        return _MISSING
    raise ConfigurationError(f"Template references missing key '{path}'.")


def _resolve_from_context(path: str, context: Any, *, allow_missing: bool) -> Any:
    current = context
    for segment in path.split("."):
        if isinstance(current, dict):
            if segment not in current:
                return _MISSING if allow_missing else _raise_missing_key(path)
            current = current[segment]
            continue
        return _MISSING if allow_missing else _raise_missing_key(path)
    return current


def _should_render_inverted_section(value: Any) -> bool:
    if value is _MISSING or value is False or value is None:
        return True
    if isinstance(value, list):
        return len(value) == 0
    if value == "":
        return True
    return False


def _raise_missing_key(path: str) -> Any:
    raise ConfigurationError(f"Template references missing key '{path}'.")


if __name__ == "__main__":
    raise SystemExit(main())
