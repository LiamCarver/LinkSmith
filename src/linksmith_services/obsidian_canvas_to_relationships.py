from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any

from linksmith_core.errors import ConfigurationError
from linksmith_core.models import JsonArtifact, JsonOutput, PortContract, ServiceContract, ServiceRunRequest
from linksmith_core.runtime import run_service


@dataclass(frozen=True)
class CanvasNode:
    id: str
    type: str
    x: float
    y: float
    width: float
    height: float
    raw: dict[str, Any]

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


def convert_canvas_document(payload: dict[str, Any]) -> dict[str, Any]:
    nodes_payload = payload.get("nodes")
    edges_payload = payload.get("edges")
    if not isinstance(nodes_payload, list):
        raise ConfigurationError("Canvas payload must contain a 'nodes' array.")
    if not isinstance(edges_payload, list):
        raise ConfigurationError("Canvas payload must contain an 'edges' array.")

    parsed_nodes = [_parse_canvas_node(item, index) for index, item in enumerate(nodes_payload)]
    groups = [node for node in parsed_nodes if node.type == "group"]
    regular_nodes = [node for node in parsed_nodes if node.type != "group"]
    group_parents = _build_group_parent_map(groups)
    group_children = _build_group_children_map(groups, group_parents)
    node_groups = _assign_nodes_to_groups(regular_nodes, groups)
    node_index = {node.id: node for node in regular_nodes}

    root_groups = [group for group in groups if group_parents[group.id] is None]
    output_groups = [
        _render_group(group, group_children, regular_nodes, node_groups)
        for group in root_groups
    ]
    ungrouped_nodes = [
        _project_node(node)
        for node in regular_nodes
        if node_groups[node.id] is None
    ]
    output_edges = [
        _project_edge(edge, node_index, node_groups, group_parents)
        for edge in edges_payload
    ]

    return {
        "groups": output_groups,
        "ungroupedNodes": ungrouped_nodes,
        "edges": output_edges,
    }


class ObsidianCanvasToRelationshipsService:
    contract = ServiceContract(
        service_id="obsidian-canvas-to-relationships",
        inputs=(
            PortContract(
                name="canvas",
                type="application/json",
                mode="file",
                cardinality="one",
            ),
        ),
        outputs=(
            PortContract(
                name="relationships",
                type="application/json",
                mode="file",
                cardinality="one",
                schema_ref="schemas/canvas-relationships.schema.json",
            ),
        ),
        version="0.1.0",
    )

    def __init__(self, output_file_name: str = "relationships.json") -> None:
        self._output_file_name = output_file_name

    def execute(self, inputs, context):
        artifact = inputs["canvas"][0]
        if not isinstance(artifact, JsonArtifact):
            raise ConfigurationError("Canvas input must be loaded as a JSON artifact.")
        if not isinstance(artifact.data, dict):
            raise ConfigurationError("Canvas input JSON root must be an object.")
        payload = convert_canvas_document(artifact.data)
        return {
            "relationships": JsonOutput(
                relative_path=PurePath(self._output_file_name),
                data=payload,
            )
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert an Obsidian canvas file into canvas-relationships JSON."
    )
    parser.add_argument("--input", required=True, help="Path to the input .canvas file.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the relationships output port folder should be written.",
    )
    parser.add_argument(
        "--output-file-name",
        default="relationships.json",
        help="Output JSON filename relative to the relationships port directory.",
    )
    parser.add_argument(
        "--schema-base-dir",
        default=".",
        help="Base directory used to resolve schemaRef values.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    service = ObsidianCanvasToRelationshipsService(output_file_name=args.output_file_name)
    request = ServiceRunRequest(
        inputs={"canvas": Path(args.input)},
        output_root=Path(args.output_dir),
        schema_base_dir=Path(args.schema_base_dir),
    )
    result = run_service(service, request)
    for port_name, paths in result.written_outputs.items():
        for path in paths:
            print(f"{port_name}: {path}")
    return 0


def _parse_canvas_node(item: Any, index: int) -> CanvasNode:
    if not isinstance(item, dict):
        raise ConfigurationError(f"Canvas node at index {index} must be an object.")
    node_id = _require_string(item, "id", f"node[{index}]")
    node_type = _require_string(item, "type", f"node[{index}]")
    x = _require_number(item, "x", f"node[{index}]")
    y = _require_number(item, "y", f"node[{index}]")
    width = _require_number(item, "width", f"node[{index}]")
    height = _require_number(item, "height", f"node[{index}]")
    return CanvasNode(
        id=node_id,
        type=node_type,
        x=x,
        y=y,
        width=width,
        height=height,
        raw=item,
    )


def _build_group_parent_map(groups: list[CanvasNode]) -> dict[str, str | None]:
    parent_map: dict[str, str | None] = {}
    for group in groups:
        containers = [candidate for candidate in groups if candidate.id != group.id and _contains(candidate, group)]
        if not containers:
            parent_map[group.id] = None
            continue
        containers.sort(key=lambda candidate: (candidate.area, candidate.id))
        parent_map[group.id] = containers[0].id
    return parent_map


def _build_group_children_map(
    groups: list[CanvasNode],
    parent_map: dict[str, str | None],
) -> dict[str, list[CanvasNode]]:
    children: dict[str, list[CanvasNode]] = {group.id: [] for group in groups}
    for group in groups:
        parent_id = parent_map[group.id]
        if parent_id is not None:
            children[parent_id].append(group)
    return children


def _assign_nodes_to_groups(
    nodes: list[CanvasNode],
    groups: list[CanvasNode],
) -> dict[str, str | None]:
    assignments: dict[str, str | None] = {}
    for node in nodes:
        containers = [group for group in groups if _contains(group, node)]
        if not containers:
            assignments[node.id] = None
            continue
        containers.sort(key=lambda candidate: (candidate.area, candidate.id))
        assignments[node.id] = containers[0].id
    return assignments


def _render_group(
    group: CanvasNode,
    group_children: dict[str, list[CanvasNode]],
    regular_nodes: list[CanvasNode],
    node_groups: dict[str, str | None],
) -> dict[str, Any]:
    child_groups = [
        _render_group(child, group_children, regular_nodes, node_groups)
        for child in group_children[group.id]
    ]
    child_nodes = [
        _project_node(node)
        for node in regular_nodes
        if node_groups[node.id] == group.id
    ]
    rendered: dict[str, Any] = {
        "id": group.id,
        "groups": child_groups,
        "nodes": child_nodes,
    }
    if isinstance(group.raw.get("label"), str) or group.raw.get("label") is None:
        rendered["label"] = group.raw.get("label")
    return rendered


def _project_node(node: CanvasNode) -> dict[str, Any]:
    projected: dict[str, Any] = {
        "id": node.id,
        "type": node.type,
    }
    for key in ("text", "label", "file", "url"):
        value = node.raw.get(key)
        if isinstance(value, str):
            projected[key] = value
    return projected


def _project_edge(
    item: Any,
    node_index: dict[str, CanvasNode],
    node_groups: dict[str, str | None],
    group_parents: dict[str, str | None],
) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ConfigurationError("Canvas edge entries must be objects.")
    from_node = _require_string(item, "fromNode", "edge")
    to_node = _require_string(item, "toNode", "edge")
    if from_node not in node_index:
        raise ConfigurationError(f"Edge references unknown fromNode '{from_node}'.")
    if to_node not in node_index:
        raise ConfigurationError(f"Edge references unknown toNode '{to_node}'.")
    from_group_id = node_groups[from_node]
    to_group_id = node_groups[to_node]
    return {
        "fromNode": from_node,
        "toNode": to_node,
        "fromGroupId": from_group_id,
        "toGroupId": to_group_id,
        "lowestSharedGroupId": _lowest_shared_group_id(from_group_id, to_group_id, group_parents),
    }


def _lowest_shared_group_id(
    left_group_id: str | None,
    right_group_id: str | None,
    group_parents: dict[str, str | None],
) -> str | None:
    if left_group_id is None or right_group_id is None:
        return None
    left_chain = _group_chain(left_group_id, group_parents)
    right_chain = _group_chain(right_group_id, group_parents)
    lowest_shared: str | None = None
    for left_value, right_value in zip(left_chain, right_chain):
        if left_value != right_value:
            break
        lowest_shared = left_value
    return lowest_shared


def _group_chain(group_id: str, group_parents: dict[str, str | None]) -> list[str]:
    chain: list[str] = []
    current: str | None = group_id
    while current is not None:
        chain.append(current)
        current = group_parents.get(current)
    chain.reverse()
    return chain


def _contains(container: CanvasNode, item: CanvasNode) -> bool:
    if item.type != "group":
        return (
            container.x <= item.x
            and container.y <= item.y
            and container.right >= item.x
            and container.bottom >= item.y
        )
    return (
        container.x <= item.x
        and container.y <= item.y
        and container.right >= item.right
        and container.bottom >= item.bottom
    )


def _require_string(item: dict[str, Any], key: str, context: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{context} is missing a non-empty string '{key}'.")
    return value


def _require_number(item: dict[str, Any], key: str, context: str) -> float:
    value = item.get(key)
    if not isinstance(value, (int, float)):
        raise ConfigurationError(f"{context} is missing numeric '{key}'.")
    return float(value)


if __name__ == "__main__":
    raise SystemExit(main())
