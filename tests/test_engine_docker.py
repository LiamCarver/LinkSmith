from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from linksmith_core.errors import SchemaValidationError
from linksmith_engine.engine import PipelineRunRequest, run_pipeline
from linksmith_engine.runtime_loader import load_runtime_config, load_service_runner
from linksmith_engine.service_runner import ServiceRunnerResult


class EngineDockerTests(unittest.TestCase):
    def test_run_pipeline_with_docker_canvas_to_markdown_services(self) -> None:
        if shutil.which("docker") is None:
            self.skipTest("Docker is not available in PATH.")

        repo_root = Path(__file__).resolve().parents[1]
        canvas_image_tag = "linksmith-obsidian-canvas-to-relationships:engine-test"
        renderer_image_tag = "linksmith-json-to-markdown-renderer:engine-test"
        pipeline_fixture_root = repo_root / "fixtures" / "pipelines" / "canvas-to-markdown"
        canvas_fixture_root = repo_root / "fixtures" / "services" / "obsidian-canvas-to-relationships"
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                str(repo_root / "services" / "obsidian-canvas-to-relationships" / "Dockerfile"),
                "-t",
                canvas_image_tag,
                str(repo_root),
            ],
            check=True,
        )
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                str(repo_root / "services" / "json-to-markdown-renderer" / "Dockerfile"),
                "-t",
                renderer_image_tag,
                str(repo_root),
            ],
            check=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            runtime_config_path = root / "runtime.json"
            canvas_file = canvas_fixture_root / "input" / "realistic-nested.canvas"
            template_file = pipeline_fixture_root / "input" / "relationships-report.template.mustache"
            registry_path.write_text(json.dumps(_canvas_markdown_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_canvas_markdown_pipeline_payload()), encoding="utf-8")
            runtime_config_path.write_text(
                json.dumps(_canvas_markdown_runtime_payload(canvas_image_tag, renderer_image_tag)),
                encoding="utf-8",
            )

            result = run_pipeline(
                PipelineRunRequest(
                    pipeline_path=pipeline_path,
                    registry_path=registry_path,
                    pipeline_inputs={
                        "canvas": canvas_file,
                        "template": template_file,
                    },
                    run_root=root / "runs",
                    run_id="run-canvas-markdown-001",
                    validate_schema=False,
                    service_runner=load_service_runner(
                        load_runtime_config(runtime_config_path, validate_schema=False)
                    ),
                )
            )

            actual_path = result.outputs["document"][0]
            expected_path = pipeline_fixture_root / "expected" / "realistic-nested-report.md"
            actual = actual_path.read_text(encoding="utf-8")
            expected = expected_path.read_text(encoding="utf-8")

            self.assertEqual(actual, expected)

    def test_run_pipeline_with_docker_markdown_renderer_service(self) -> None:
        if shutil.which("docker") is None:
            self.skipTest("Docker is not available in PATH.")

        repo_root = Path(__file__).resolve().parents[1]
        fixture_root = repo_root / "fixtures" / "services" / "json-to-markdown-renderer"
        image_tag = "linksmith-json-to-markdown-renderer:engine-test"
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                str(repo_root / "services" / "json-to-markdown-renderer" / "Dockerfile"),
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
            data_file = fixture_root / "input" / "basic-report.data.json"
            template_file = fixture_root / "input" / "basic-report.template.mustache"
            registry_path.write_text(json.dumps(_renderer_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_renderer_pipeline_payload()), encoding="utf-8")
            runtime_config_path.write_text(json.dumps(_renderer_runtime_payload(image_tag)), encoding="utf-8")

            result = run_pipeline(
                PipelineRunRequest(
                    pipeline_path=pipeline_path,
                    registry_path=registry_path,
                    pipeline_inputs={
                        "data": data_file,
                        "template": template_file,
                    },
                    run_root=root / "runs",
                    run_id="run-renderer-001",
                    validate_schema=False,
                    service_runner=load_service_runner(
                        load_runtime_config(runtime_config_path, validate_schema=False)
                    ),
                )
            )

            actual_path = result.outputs["document"][0]
            expected_path = fixture_root / "expected" / "basic-report.document.md"
            actual = actual_path.read_text(encoding="utf-8")
            expected = expected_path.read_text(encoding="utf-8")

            self.assertEqual(actual, expected)

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
                    validate_outputs=True,
                    service_runner=load_service_runner(
                        load_runtime_config(runtime_config_path, validate_schema=False)
                    ),
                )
            )

            output_file = result.outputs["relationships"][0]
            payload = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["groups"][0]["id"], "group-one")
            self.assertEqual(payload["groups"][0]["nodes"][0]["id"], "node-one")

    def test_run_pipeline_routes_real_docker_output_into_downstream_fake_service(self) -> None:
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
            registry_path.write_text(json.dumps(_mixed_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_mixed_pipeline_payload()), encoding="utf-8")
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

            docker_runner = load_service_runner(load_runtime_config(runtime_config_path, validate_schema=False))
            result = run_pipeline(
                PipelineRunRequest(
                    pipeline_path=pipeline_path,
                    registry_path=registry_path,
                    pipeline_inputs={"canvas": input_canvas},
                    run_root=root / "runs",
                    run_id="run-002",
                    validate_schema=False,
                    service_runner=MixedServiceRunner(docker_runner=docker_runner),
                )
            )

            output_file = result.outputs["question_bundle"][0]
            payload = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["groupCount"], 1)
            self.assertEqual(payload["ungroupedNodeCount"], 0)
            self.assertEqual(payload["questions"][0], "Which principle best fits group-one?")

    def test_run_pipeline_rejects_invalid_downstream_output_after_real_docker_step(self) -> None:
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
            registry_path.write_text(
                json.dumps(_mixed_invalid_registry_payload(_questions_schema_path())),
                encoding="utf-8",
            )
            pipeline_path.write_text(json.dumps(_mixed_invalid_pipeline_payload()), encoding="utf-8")
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

            docker_runner = load_service_runner(load_runtime_config(runtime_config_path, validate_schema=False))
            with self.assertRaises(SchemaValidationError):
                run_pipeline(
                    PipelineRunRequest(
                        pipeline_path=pipeline_path,
                        registry_path=registry_path,
                        pipeline_inputs={"canvas": input_canvas},
                        run_root=root / "runs",
                        run_id="run-003",
                        validate_schema=False,
                        validate_outputs=True,
                        service_runner=MixedInvalidServiceRunner(docker_runner=docker_runner),
                    )
                )

    def test_run_pipeline_writes_failed_manifests_after_real_docker_upstream_success(self) -> None:
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
            registry_path.write_text(json.dumps(_mixed_failure_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_mixed_failure_pipeline_payload()), encoding="utf-8")
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

            docker_runner = load_service_runner(load_runtime_config(runtime_config_path, validate_schema=False))
            with self.assertRaisesRegex(RuntimeError, "simulated mixed downstream failure"):
                run_pipeline(
                    PipelineRunRequest(
                        pipeline_path=pipeline_path,
                        registry_path=registry_path,
                        pipeline_inputs={"canvas": input_canvas},
                        run_root=root / "runs",
                        run_id="run-004",
                        validate_schema=False,
                        service_runner=MixedFailingServiceRunner(docker_runner=docker_runner),
                    )
                )

            run_manifest = json.loads((root / "runs" / "run-004" / "manifests" / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(run_manifest["status"], "failed")
            self.assertIn("simulated mixed downstream failure", run_manifest["error"])
            self.assertEqual(run_manifest["outputs"], {})
            self.assertEqual(len(run_manifest["invocationManifests"]), 2)

            upstream_manifest = json.loads(
                (root / "runs" / "run-004" / "manifests" / "invocations" / "normalize.canvas.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(upstream_manifest["status"], "succeeded")

            failed_manifest = json.loads(
                (root / "runs" / "run-004" / "manifests" / "invocations" / "bundle.questions.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(failed_manifest["status"], "failed")
            self.assertIn("simulated mixed downstream failure", failed_manifest["error"])
            self.assertEqual(failed_manifest["outputs"], {})


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


def _renderer_registry_payload() -> dict[str, object]:
    return {
        "services": [
            {
                "id": "json-to-markdown-renderer",
                "kind": "render",
                "deterministic": True,
                "description": "Render Markdown from JSON and a Mustache template.",
                "entrypoint": "docker://json-to-markdown-renderer",
                "inputs": [
                    {"name": "data", "type": "json-document", "mode": "file", "cardinality": "one"},
                    {"name": "template", "type": "mustache-template", "mode": "file", "cardinality": "one"},
                ],
                "outputs": [
                    {"name": "document", "type": "markdown-document", "mode": "file", "cardinality": "one"}
                ],
            }
        ]
    }


def _renderer_pipeline_payload() -> dict[str, object]:
    return {
        "id": "render-basic-report",
        "inputs": [
            {"name": "data", "type": "json-document", "mode": "file", "cardinality": "one"},
            {"name": "template", "type": "mustache-template", "mode": "file", "cardinality": "one"},
        ],
        "outputs": [
            {"name": "document", "type": "markdown-document", "mode": "file", "cardinality": "one"}
        ],
        "steps": [
            {"id": "render", "invocations": [{"id": "report", "service": "json-to-markdown-renderer"}]}
        ],
        "edges": [
            {"from": "pipeline:input.data", "to": "render.report.data"},
            {"from": "pipeline:input.template", "to": "render.report.template"},
            {"from": "render.report.document", "to": "pipeline:output.document"},
        ],
    }


def _renderer_runtime_payload(image_tag: str) -> dict[str, object]:
    return {
        "runner": {
            "kind": "docker",
            "services": {
                "json-to-markdown-renderer": {
                    "image": image_tag,
                    "inputArguments": {
                        "data": "--data",
                        "template": "--template",
                    },
                    "outputDirArgument": "--output-dir",
                    "outputFileNameArguments": {"document": "--output-file-name"},
                    "outputFileNames": {"document": "document.md"},
                    "inputMountRoot": "/data/inputs",
                    "outputMountRoot": "/data/output",
                }
            }
        }
    }


def _canvas_markdown_registry_payload() -> dict[str, object]:
    return {
        "services": [
            {
                "id": "obsidian-canvas-to-relationships",
                "kind": "transform",
                "deterministic": True,
                "description": "Convert an Obsidian canvas file into relationships JSON.",
                "entrypoint": "docker://obsidian-canvas-to-relationships",
                "inputs": [
                    {"name": "canvas", "type": "obsidian-canvas", "mode": "file", "cardinality": "one"}
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
            },
            {
                "id": "json-to-markdown-renderer",
                "kind": "render",
                "deterministic": True,
                "description": "Render Markdown from relationships JSON and a Mustache template.",
                "entrypoint": "docker://json-to-markdown-renderer",
                "inputs": [
                    {
                        "name": "data",
                        "type": "canvas-relationships",
                        "mode": "file",
                        "cardinality": "one",
                    },
                    {"name": "template", "type": "mustache-template", "mode": "file", "cardinality": "one"},
                ],
                "outputs": [
                    {"name": "document", "type": "markdown-document", "mode": "file", "cardinality": "one"}
                ],
            },
        ]
    }


def _canvas_markdown_pipeline_payload() -> dict[str, object]:
    return {
        "id": "canvas-to-markdown",
        "inputs": [
            {"name": "canvas", "type": "obsidian-canvas", "mode": "file", "cardinality": "one"},
            {"name": "template", "type": "mustache-template", "mode": "file", "cardinality": "one"},
        ],
        "outputs": [
            {"name": "document", "type": "markdown-document", "mode": "file", "cardinality": "one"}
        ],
        "steps": [
            {"id": "normalize", "invocations": [{"id": "canvas", "service": "obsidian-canvas-to-relationships"}]},
            {"id": "render", "invocations": [{"id": "report", "service": "json-to-markdown-renderer"}]},
        ],
        "edges": [
            {"from": "pipeline:input.canvas", "to": "normalize.canvas.canvas"},
            {"from": "normalize.canvas.relationships", "to": "render.report.data"},
            {"from": "pipeline:input.template", "to": "render.report.template"},
            {"from": "render.report.document", "to": "pipeline:output.document"},
        ],
    }


def _canvas_markdown_runtime_payload(
    canvas_image_tag: str, renderer_image_tag: str
) -> dict[str, object]:
    return {
        "runner": {
            "kind": "docker",
            "services": {
                "obsidian-canvas-to-relationships": {
                    "image": canvas_image_tag,
                    "inputArguments": {"canvas": "--input"},
                    "outputDirArgument": "--output-dir",
                    "outputFileNameArguments": {"relationships": "--output-file-name"},
                    "outputFileNames": {"relationships": "relationships.json"},
                    "schemaBaseDirArgument": "--schema-base-dir",
                    "schemaBaseDirValue": "/app",
                    "inputMountRoot": "/data/inputs",
                    "outputMountRoot": "/data/output",
                },
                "json-to-markdown-renderer": {
                    "image": renderer_image_tag,
                    "inputArguments": {
                        "data": "--data",
                        "template": "--template",
                    },
                    "outputDirArgument": "--output-dir",
                    "outputFileNameArguments": {"document": "--output-file-name"},
                    "outputFileNames": {"document": "document.md"},
                    "inputMountRoot": "/data/inputs",
                    "outputMountRoot": "/data/output",
                },
            },
        }
    }


def _mixed_registry_payload() -> dict[str, object]:
    return {
        "services": [
            {
                "id": "obsidian-canvas-to-relationships",
                "kind": "transform",
                "deterministic": True,
                "description": "Convert an Obsidian canvas file into relationships JSON.",
                "entrypoint": "docker://obsidian-canvas-to-relationships",
                "inputs": [
                    {"name": "canvas", "type": "obsidian-canvas", "mode": "file", "cardinality": "one"}
                ],
                "outputs": [
                    {"name": "relationships", "type": "canvas-relationships", "mode": "file", "cardinality": "one"}
                ],
            },
            {
                "id": "build-question-bundle",
                "kind": "transform",
                "deterministic": True,
                "description": "Build question bundle from relationships JSON.",
                "entrypoint": "python://build-question-bundle",
                "inputs": [
                    {"name": "relationships", "type": "canvas-relationships", "mode": "file", "cardinality": "one"}
                ],
                "outputs": [
                    {"name": "question_bundle", "type": "questions-json", "mode": "file", "cardinality": "one"}
                ],
            }
        ]
    }


def _mixed_pipeline_payload() -> dict[str, object]:
    return {
        "id": "canvas-question-bundle",
        "inputs": [
            {"name": "canvas", "type": "obsidian-canvas", "mode": "file", "cardinality": "one"}
        ],
        "outputs": [
            {"name": "question_bundle", "type": "questions-json", "mode": "file", "cardinality": "one"}
        ],
        "steps": [
            {"id": "normalize", "invocations": [{"id": "canvas", "service": "obsidian-canvas-to-relationships"}]},
            {"id": "bundle", "invocations": [{"id": "questions", "service": "build-question-bundle"}]}
        ],
        "edges": [
            {"from": "pipeline:input.canvas", "to": "normalize.canvas.canvas"},
            {"from": "normalize.canvas.relationships", "to": "bundle.questions.relationships"},
            {"from": "bundle.questions.question_bundle", "to": "pipeline:output.question_bundle"}
        ],
    }


def _mixed_invalid_registry_payload(questions_schema_path: str) -> dict[str, object]:
    return {
        "services": [
            {
                "id": "obsidian-canvas-to-relationships",
                "kind": "transform",
                "deterministic": True,
                "description": "Convert an Obsidian canvas file into relationships JSON.",
                "entrypoint": "docker://obsidian-canvas-to-relationships",
                "inputs": [
                    {"name": "canvas", "type": "obsidian-canvas", "mode": "file", "cardinality": "one"}
                ],
                "outputs": [
                    {"name": "relationships", "type": "canvas-relationships", "mode": "file", "cardinality": "one"}
                ],
            },
            {
                "id": "build-invalid-question-bundle",
                "kind": "transform",
                "deterministic": True,
                "description": "Emit invalid question bundle payload.",
                "entrypoint": "python://build-invalid-question-bundle",
                "inputs": [
                    {"name": "relationships", "type": "canvas-relationships", "mode": "file", "cardinality": "one"}
                ],
                "outputs": [
                    {
                        "name": "question_bundle",
                        "type": "questions-json",
                        "mode": "file",
                        "cardinality": "one",
                        "schemaRef": questions_schema_path
                    }
                ],
            }
        ]
    }


def _mixed_invalid_pipeline_payload() -> dict[str, object]:
    return {
        "id": "invalid-canvas-question-bundle",
        "inputs": [
            {"name": "canvas", "type": "obsidian-canvas", "mode": "file", "cardinality": "one"}
        ],
        "outputs": [
            {"name": "question_bundle", "type": "questions-json", "mode": "file", "cardinality": "one"}
        ],
        "steps": [
            {"id": "normalize", "invocations": [{"id": "canvas", "service": "obsidian-canvas-to-relationships"}]},
            {"id": "bundle", "invocations": [{"id": "questions", "service": "build-invalid-question-bundle"}]}
        ],
        "edges": [
            {"from": "pipeline:input.canvas", "to": "normalize.canvas.canvas"},
            {"from": "normalize.canvas.relationships", "to": "bundle.questions.relationships"},
            {"from": "bundle.questions.question_bundle", "to": "pipeline:output.question_bundle"}
        ],
    }


def _mixed_failure_registry_payload() -> dict[str, object]:
    return {
        "services": [
            {
                "id": "obsidian-canvas-to-relationships",
                "kind": "transform",
                "deterministic": True,
                "description": "Convert an Obsidian canvas file into relationships JSON.",
                "entrypoint": "docker://obsidian-canvas-to-relationships",
                "inputs": [
                    {"name": "canvas", "type": "obsidian-canvas", "mode": "file", "cardinality": "one"}
                ],
                "outputs": [
                    {"name": "relationships", "type": "canvas-relationships", "mode": "file", "cardinality": "one"}
                ],
            },
            {
                "id": "build-failing-question-bundle",
                "kind": "transform",
                "deterministic": True,
                "description": "Raise failure after upstream docker success.",
                "entrypoint": "python://build-failing-question-bundle",
                "inputs": [
                    {"name": "relationships", "type": "canvas-relationships", "mode": "file", "cardinality": "one"}
                ],
                "outputs": [
                    {"name": "question_bundle", "type": "questions-json", "mode": "file", "cardinality": "one"}
                ],
            }
        ]
    }


def _mixed_failure_pipeline_payload() -> dict[str, object]:
    return {
        "id": "failing-canvas-question-bundle",
        "inputs": [
            {"name": "canvas", "type": "obsidian-canvas", "mode": "file", "cardinality": "one"}
        ],
        "outputs": [
            {"name": "question_bundle", "type": "questions-json", "mode": "file", "cardinality": "one"}
        ],
        "steps": [
            {"id": "normalize", "invocations": [{"id": "canvas", "service": "obsidian-canvas-to-relationships"}]},
            {"id": "bundle", "invocations": [{"id": "questions", "service": "build-failing-question-bundle"}]}
        ],
        "edges": [
            {"from": "pipeline:input.canvas", "to": "normalize.canvas.canvas"},
            {"from": "normalize.canvas.relationships", "to": "bundle.questions.relationships"},
            {"from": "bundle.questions.question_bundle", "to": "pipeline:output.question_bundle"}
        ],
    }


class MixedServiceRunner:
    def __init__(self, *, docker_runner) -> None:
        self._docker_runner = docker_runner

    def run(self, request):
        if request.service_id == "obsidian-canvas-to-relationships":
            return self._docker_runner.run(request)
        if request.service_id == "build-question-bundle":
            relationships = json.loads(request.inputs["relationships"][0].read_text(encoding="utf-8"))
            request.output_root.mkdir(parents=True, exist_ok=True)
            output_file = request.output_root / "question_bundle" / "question-bundle.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                json.dumps(
                    {
                        "groupCount": len(relationships["groups"]),
                        "ungroupedNodeCount": len(relationships["ungroupedNodes"]),
                        "questions": ["Which principle best fits group-one?"],
                    }
                ),
                encoding="utf-8",
            )
            request.log_path.parent.mkdir(parents=True, exist_ok=True)
            request.log_path.write_text("mixed-runner ok", encoding="utf-8")
            return ServiceRunnerResult(outputs={"question_bundle": (output_file,)}, exit_code=0)
        raise AssertionError(f"Unexpected service id: {request.service_id}")


class MixedInvalidServiceRunner:
    def __init__(self, *, docker_runner) -> None:
        self._docker_runner = docker_runner

    def run(self, request):
        if request.service_id == "obsidian-canvas-to-relationships":
            return self._docker_runner.run(request)
        if request.service_id == "build-invalid-question-bundle":
            request.output_root.mkdir(parents=True, exist_ok=True)
            output_file = request.output_root / "question_bundle" / "question-bundle.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                json.dumps({"questions": ["not-an-object"]}),
                encoding="utf-8",
            )
            request.log_path.parent.mkdir(parents=True, exist_ok=True)
            request.log_path.write_text("mixed-invalid-runner ok", encoding="utf-8")
            return ServiceRunnerResult(outputs={"question_bundle": (output_file,)}, exit_code=0)
        raise AssertionError(f"Unexpected service id: {request.service_id}")


class MixedFailingServiceRunner:
    def __init__(self, *, docker_runner) -> None:
        self._docker_runner = docker_runner

    def run(self, request):
        if request.service_id == "obsidian-canvas-to-relationships":
            return self._docker_runner.run(request)
        if request.service_id == "build-failing-question-bundle":
            request.log_path.parent.mkdir(parents=True, exist_ok=True)
            request.log_path.write_text("mixed-failing-runner boom", encoding="utf-8")
            raise RuntimeError("simulated mixed downstream failure")
        raise AssertionError(f"Unexpected service id: {request.service_id}")


def _questions_schema_path() -> str:
    return str((Path(__file__).resolve().parents[1] / "schemas" / "questions.schema.json").resolve())


if __name__ == "__main__":
    unittest.main()
