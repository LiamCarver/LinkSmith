from __future__ import annotations

import argparse
from pathlib import Path, PurePath
from typing import Any

from linksmith_core.errors import ConfigurationError
from linksmith_core.models import JsonArtifact, MarkdownOutput, PortContract, ServiceContract, ServiceRunRequest
from linksmith_core.runtime import run_service
from linksmith_engine.models import EnginePipelineDefinition, InvocationDefinition, PipelineEdge, StepDefinition
from linksmith_engine.pipeline_loader import parse_pipeline_payload


def render_pipeline_document(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        raise ConfigurationError("Pipeline renderer JSON root must be an object.")
    pipeline = parse_pipeline_payload(payload, definition_path=Path("pipeline.json"))
    rendered = _render_pipeline_markdown(pipeline)
    if not rendered.strip():
        raise ConfigurationError("Rendered pipeline Markdown output must not be empty.")
    return rendered


class PipelineJsonToMarkdownRendererService:
    contract = ServiceContract(
        service_id="pipeline-json-to-markdown-renderer",
        inputs=(
            PortContract(
                name="pipeline",
                type="linksmith-pipeline-definition",
                mode="file",
                cardinality="one",
                schema_ref="schemas/pipeline.schema.json",
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
        artifact = inputs["pipeline"][0]
        if not isinstance(artifact, JsonArtifact):
            raise ConfigurationError("Pipeline renderer input must be loaded as a JSON artifact.")
        if not isinstance(artifact.data, dict):
            raise ConfigurationError("Pipeline renderer JSON root must be an object.")
        rendered = render_pipeline_document(artifact.data)
        return {
            "document": MarkdownOutput(
                relative_path=PurePath(self._output_file_name),
                text=rendered,
            )
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a LinkSmith pipeline definition into Markdown with Mermaid."
    )
    parser.add_argument("--pipeline", required=True, help="Path to the pipeline JSON input file.")
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
    parser.add_argument(
        "--schema-base-dir",
        default=".",
        help="Base directory used to resolve schemaRef values.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    service = PipelineJsonToMarkdownRendererService(output_file_name=args.output_file_name)
    request = ServiceRunRequest(
        inputs={"pipeline": Path(args.pipeline)},
        output_root=Path(args.output_dir),
        schema_base_dir=Path(args.schema_base_dir),
    )
    result = run_service(service, request)
    for port_name, paths in result.written_outputs.items():
        for path in paths:
            print(f"{port_name}: {path}")
    return 0


def _render_pipeline_markdown(pipeline: EnginePipelineDefinition) -> str:
    title = pipeline.name or pipeline.pipeline_id
    lines = [f"# {title}", "", f"`{pipeline.pipeline_id}`", ""]
    if pipeline.description:
        lines.extend([pipeline.description, ""])

    lines.extend(["## Inputs", ""])
    if pipeline.inputs:
        for port in pipeline.inputs:
            lines.append(f"- {_render_port_summary(port)}")
    else:
        lines.append("- None")
    lines.append("")

    lines.extend(["## Outputs", ""])
    if pipeline.outputs:
        for port in pipeline.outputs:
            lines.append(f"- {_render_port_summary(port)}")
    else:
        lines.append("- None")
    lines.append("")

    lines.extend(["## Steps", ""])
    for step in pipeline.steps:
        lines.extend(_render_step(step))
    lines.extend(["## Edges", ""])
    for edge in pipeline.edges:
        lines.append(f"- `{edge.from_endpoint}` -> `{edge.to_endpoint}`")
    lines.extend(["", "## Mermaid", "", "```mermaid", "flowchart TD"])
    lines.extend(_render_mermaid_lines(pipeline))
    lines.append("```")
    return "\n".join(lines) + "\n"


def _render_port_summary(port: PortContract) -> str:
    description = f": {port.description}" if port.description else ""
    return f"`{port.name}` (`{port.type}`, `{port.mode}`, `{port.cardinality}`){description}"


def _render_step(step: StepDefinition) -> list[str]:
    lines = [f"### `{step.step_id}`", ""]
    if step.description:
        lines.extend([step.description, ""])
    for invocation in step.invocations:
        lines.append(f"- Invocation: `{step.step_id}.{invocation.invocation_id}`")
        lines.append(f"- Service: `{invocation.service_id}`")
        for resource in invocation.resources:
            lines.append(
                f"- Resource: `{resource.name}` (`{resource.type}`, `{resource.mode}`, `{resource.cardinality}`) -> `{resource.path}`"
            )
        lines.append("")
    return lines


def _render_mermaid_lines(pipeline: EnginePipelineDefinition) -> list[str]:
    lines: list[str] = []
    rendered_nodes: set[str] = set()
    for endpoint in _ordered_mermaid_nodes(pipeline):
        if endpoint in rendered_nodes:
            continue
        lines.append(_render_mermaid_node_line(pipeline, endpoint))
        rendered_nodes.add(endpoint)
    for edge in pipeline.edges:
        lines.append(
            f"    {_node_id(_source_node_key(edge))} -->|{_edge_label(edge)}| {_node_id(_target_node_key(edge))}"
        )
    return lines


def _ordered_mermaid_nodes(pipeline: EnginePipelineDefinition) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def add(endpoint: str) -> None:
        if endpoint not in seen:
            ordered.append(endpoint)
            seen.add(endpoint)

    for edge in pipeline.edges:
        add(_source_node_key(edge))
        add(_target_node_key(edge))

    for port in pipeline.inputs:
        add(f"pipeline:input.{port.name}")
    for step in pipeline.steps:
        for invocation in step.invocations:
            add(f"{step.step_id}.{invocation.invocation_id}")
    for port in pipeline.outputs:
        add(f"pipeline:output.{port.name}")

    return ordered


def _render_mermaid_node_line(pipeline: EnginePipelineDefinition, endpoint: str) -> str:
    if endpoint.startswith("pipeline:"):
        return f'    {_node_id(endpoint)}["{endpoint}"]'

    invocation = _find_invocation(pipeline, endpoint)
    label = f"{endpoint}\\n{invocation.service_id}"
    return f'    {_node_id(endpoint)}["{label}"]'


def _find_invocation(
    pipeline: EnginePipelineDefinition,
    endpoint: str,
) -> InvocationDefinition:
    step_id, invocation_id = endpoint.split(".", 1)
    for step in pipeline.steps:
        if step.step_id != step_id:
            continue
        for invocation in step.invocations:
            if invocation.invocation_id == invocation_id:
                return invocation
    raise ConfigurationError(f"Pipeline references unknown invocation '{endpoint}'.")


def _node_id(value: str) -> str:
    cleaned = []
    for char in value:
        if char.isalnum():
            cleaned.append(char)
        else:
            cleaned.append("_")
    return "".join(cleaned).strip("_")


def _source_node_key(edge: PipelineEdge) -> str:
    if edge.from_endpoint.startswith("pipeline:"):
        return edge.from_endpoint
    return ".".join(edge.from_endpoint.split(".")[:2])


def _target_node_key(edge: PipelineEdge) -> str:
    if edge.to_endpoint.startswith("pipeline:"):
        return edge.to_endpoint
    return ".".join(edge.to_endpoint.split(".")[:2])


def _edge_label(edge: PipelineEdge) -> str:
    source_port = edge.from_endpoint.split(".")[-1]
    target_port = edge.to_endpoint.split(".")[-1]
    if edge.from_endpoint.startswith("pipeline:input."):
        return source_port
    if edge.to_endpoint.startswith("pipeline:output."):
        return f"{source_port} -> {target_port}"
    return f"{source_port} -> {target_port}"


if __name__ == "__main__":
    raise SystemExit(main())
