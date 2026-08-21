from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from linksmith_engine.engine import PipelineRunRequest, run_pipeline
from linksmith_engine.service_runner import DockerServiceConfig, DockerServiceRunner


class EngineDockerTests(unittest.TestCase):
    def test_run_pipeline_with_docker_service_runner(self) -> None:
        if shutil.which("docker") is None:
            self.skipTest("Docker is not available in PATH.")

        repo_root = Path(__file__).resolve().parents[1]
        image_tag = "linksmith-obsidian-canvas-to-relationships:engine-test"
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                str(repo_root / "services" / "obsidian-canvas-to-relationships" / "Dockerfile"),
                "-t",
                image_tag,
                str(repo_root),
            ],
            check=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            input_canvas = root / "input.canvas"
            registry_path.write_text(json.dumps(_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_pipeline_payload()), encoding="utf-8")
            input_canvas.write_text(
                json.dumps(
                    {
                        "nodes": [
                            {"id": "group-one", "type": "group", "x": 0, "y": 0, "width": 200, "height": 200, "label": "Group"},
                            {"id": "node-one", "type": "text", "x": 10, "y": 20, "width": 100, "height": 50, "text": "Hello"},
                        ],
                        "edges": [],
                    }
                ),
                encoding="utf-8",
            )

            result = run_pipeline(
                PipelineRunRequest(
                    pipeline_path=pipeline_path,
                    registry_path=registry_path,
                    pipeline_inputs={"canvas": input_canvas},
                    run_root=root / "runs",
                    run_id="run-001",
                    validate_schema=False,
                    service_runner=DockerServiceRunner(
                        {
                            "obsidian-canvas-to-relationships": DockerServiceConfig(
                                image=image_tag,
                                input_arguments={"canvas": "--input"},
                                output_dir_argument="--output-dir",
                                output_file_name_arguments={"relationships": "--output-file-name"},
                                output_file_names={"relationships": "relationships.json"},
                                schema_base_dir_argument="--schema-base-dir",
                                schema_base_dir_value="/app",
                                output_mount_root="/data/output",
                                input_mount_root="/data/inputs",
                            )
                        }
                    ),
                )
            )

            output_file = result.outputs["relationships"][0]
            payload = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["groups"][0]["id"], "group-one")
            self.assertEqual(payload["groups"][0]["nodes"][0]["id"], "node-one")


def _registry_payload() -> dict[str, object]:
    return {
        "services": [
            {
                "id": "obsidian-canvas-to-relationships",
                "kind": "transform",
                "deterministic": True,
                "description": "Convert an Obsidian canvas file into relationships JSON.",
                "entrypoint": "docker://obsidian-canvas-to-relationships",
                "inputs": [
                    {
                        "name": "canvas",
                        "type": "obsidian-canvas",
                        "mode": "file",
                        "cardinality": "one",
                    }
                ],
                "outputs": [
                    {
                        "name": "relationships",
                        "type": "canvas-relationships",
                        "mode": "file",
                        "cardinality": "one",
                        "schemaRef": "schemas/canvas-relationships.schema.json",
                    }
                ],
            }
        ]
    }


def _pipeline_payload() -> dict[str, object]:
    return {
        "id": "canvas-normalize",
        "inputs": [
            {"name": "canvas", "type": "obsidian-canvas", "mode": "file", "cardinality": "one"}
        ],
        "outputs": [
            {"name": "relationships", "type": "canvas-relationships", "mode": "file", "cardinality": "one"}
        ],
        "steps": [
            {"id": "normalize", "invocations": [{"id": "canvas", "service": "obsidian-canvas-to-relationships"}]}
        ],
        "edges": [
            {"from": "pipeline:input.canvas", "to": "normalize.canvas.canvas"},
            {"from": "normalize.canvas.relationships", "to": "pipeline:output.relationships"},
        ],
    }


if __name__ == "__main__":
    unittest.main()
