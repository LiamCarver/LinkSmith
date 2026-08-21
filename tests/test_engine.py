from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from linksmith_engine.engine import PipelineRunRequest, run_pipeline
from linksmith_engine.pipeline_loader import load_pipeline_definition
from linksmith_engine.registry_loader import load_registry_document
from linksmith_engine.runtime_loader import load_runtime_config, load_service_runner
from linksmith_engine.service_runner import DockerServiceConfig, DockerServiceRunner, ServiceRunnerRequest, ServiceRunnerResult
from linksmith_core.models import PortContract
from linksmith_engine.validator import validate_pipeline_semantics


class FakeServiceRunner:
    def run(self, request):
        request.output_root.mkdir(parents=True, exist_ok=True)
        output_file = request.output_root / "relationships" / "relationships.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps({"groups": [], "ungroupedNodes": [], "edges": []}),
            encoding="utf-8",
        )
        request.log_path.parent.mkdir(parents=True, exist_ok=True)
        request.log_path.write_text("fake-runner ok", encoding="utf-8")
        return ServiceRunnerResult(outputs={"relationships": (output_file,)}, exit_code=0)


class EngineTests(unittest.TestCase):
    def test_semantic_validation_accepts_single_invocation_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            registry_path.write_text(json.dumps(_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_pipeline_payload()), encoding="utf-8")

            registry = load_registry_document(registry_path, validate_schema=False)
            pipeline = load_pipeline_definition(pipeline_path, validate_schema=False)

            validate_pipeline_semantics(pipeline, registry)

    def test_run_pipeline_creates_run_layout_and_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            input_canvas = root / "input.canvas"
            registry_path.write_text(json.dumps(_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_pipeline_payload()), encoding="utf-8")
            input_canvas.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")

            result = run_pipeline(
                PipelineRunRequest(
                    pipeline_path=pipeline_path,
                    registry_path=registry_path,
                    pipeline_inputs={"canvas": input_canvas},
                    run_root=root / "runs",
                    service_runner=FakeServiceRunner(),
                    run_id="run-001",
                    validate_schema=False,
                )
            )

            output_file = result.outputs["relationships"][0]
            self.assertTrue(output_file.exists())
            self.assertEqual(json.loads(output_file.read_text(encoding="utf-8")), {"groups": [], "ungroupedNodes": [], "edges": []})
            self.assertTrue(result.run_paths.run_manifest_file.exists())
            self.assertEqual(len(result.invocation_manifests), 1)

    def test_load_runtime_config_resolves_docker_service_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_config_path = root / "runtime.json"
            runtime_config_path.write_text(json.dumps(_runtime_payload()), encoding="utf-8")

            runtime_config = load_runtime_config(runtime_config_path, validate_schema=False)
            runner = load_service_runner(runtime_config)

            self.assertEqual(runtime_config.runner_kind, "docker")
            self.assertIsInstance(runner, DockerServiceRunner)
            config = runner._service_configs["obsidian-canvas-to-relationships"]
            self.assertEqual(config.image, "linksmith-obsidian-canvas-to-relationships:test")
            self.assertEqual(config.input_arguments["canvas"], "--input")
            self.assertEqual(config.output_file_names["relationships"], "relationships.json")

    def test_docker_service_runner_places_service_arguments_after_image(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_file = root / "input.canvas"
            output_root = root / "outputs"
            log_path = root / "runner.log"
            input_file.write_text("{}", encoding="utf-8")

            request = ServiceRunnerRequest(
                step_id="normalize",
                invocation_id="canvas",
                service_id="obsidian-canvas-to-relationships",
                inputs={"canvas": (input_file,)},
                input_contracts={
                    "canvas": PortContract(
                        name="canvas",
                        type="obsidian-canvas",
                        mode="file",
                        cardinality="one",
                    )
                },
                output_contracts={
                    "relationships": PortContract(
                        name="relationships",
                        type="canvas-relationships",
                        mode="file",
                        cardinality="one",
                    )
                },
                output_root=output_root,
                config={},
                log_path=log_path,
            )
            runner = DockerServiceRunner(
                {
                    "obsidian-canvas-to-relationships": DockerServiceConfig(
                        image="example-image:latest",
                        input_arguments={"canvas": "--input"},
                        output_dir_argument="--output-dir",
                        output_file_name_arguments={"relationships": "--output-file-name"},
                        output_file_names={"relationships": "relationships.json"},
                        input_mount_root="/data/inputs",
                        output_mount_root="/data/output",
                    )
                }
            )

            with patch("linksmith_engine.service_runner.which", return_value="docker"), patch(
                "linksmith_engine.service_runner.subprocess.run"
            ) as mocked_run:
                mocked_run.return_value.returncode = 0
                mocked_run.return_value.stdout = "ok"

                runner.run(request)

            command = mocked_run.call_args.args[0]
            image_index = command.index("example-image:latest")
            self.assertLess(image_index, command.index("--input"))
            self.assertEqual(command[0:3], ["docker", "run", "--rm"])


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
            }
        ],
        "steps": [
            {
                "id": "normalize",
                "invocations": [
                    {
                        "id": "canvas",
                        "service": "obsidian-canvas-to-relationships",
                    }
                ],
            }
        ],
        "edges": [
            {
                "from": "pipeline:input.canvas",
                "to": "normalize.canvas.canvas",
            },
            {
                "from": "normalize.canvas.relationships",
                "to": "pipeline:output.relationships",
            },
        ],
    }


def _runtime_payload() -> dict[str, object]:
    return {
        "runner": {
            "kind": "docker",
            "services": {
                "obsidian-canvas-to-relationships": {
                    "image": "linksmith-obsidian-canvas-to-relationships:test",
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
