from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from linksmith_engine.engine import PipelineRunRequest, run_pipeline
from linksmith_engine.runtime_loader import load_runtime_config, load_service_runner


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
            runtime_config_path = root / "runtime.json"
            input_canvas = root / "input.canvas"
            registry_path.write_text(json.dumps(_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_pipeline_payload()), encoding="utf-8")
            runtime_config_path.write_text(json.dumps(_runtime_payload(image_tag)), encoding="utf-8")
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
                    service_runner=load_service_runner(
                        load_runtime_config(runtime_config_path, validate_schema=False)
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


def _runtime_payload(image_tag: str) -> dict[str, object]:
    return {
        "runner": {
            "kind": "docker",
            "services": {
                "obsidian-canvas-to-relationships": {
                    "image": image_tag,
                    "inputArguments": {"canvas": "--input"},
                    "outputDirArgument": "--output-dir",
                    "outputFileNameArguments": {"relationships": "--output-file-name"},
                    "outputFileNames": {"relationships": "relationships.json"},
                    "schemaBaseDirArgument": "--schema-base-dir",
                    "schemaBaseDirValue": "/app",
                    "inputMountRoot": "/data/inputs",
                    "outputMountRoot": "/data/output"
                }
            }
        }
    }


if __name__ == "__main__":
    unittest.main()
