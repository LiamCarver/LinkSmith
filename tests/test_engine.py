from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from linksmith_core.errors import ConfigurationError, SchemaValidationError
from linksmith_engine.engine import PipelineRunRequest, run_pipeline
from linksmith_engine.errors import PipelineValidationError
from linksmith_engine.pipeline_loader import load_pipeline_definition
from linksmith_engine.registry_loader import load_registry_document
from linksmith_engine.runtime_loader import load_runtime_config, load_service_runner
from linksmith_engine.service_runner import DockerServiceConfig, DockerServiceRunner, ServiceRunnerRequest, ServiceRunnerResult
from linksmith_core.models import PortContract
from linksmith_engine.validator import validate_pipeline_semantics
from tests.json_fixtures import load_fixture_json


def _engine_payload(name: str, *, substitutions: dict[str, str] | None = None):
    return load_fixture_json("engine/payloads.json", key=name, substitutions=substitutions)


class FakeServiceRunner:
    def run(self, request):
        request.output_root.mkdir(parents=True, exist_ok=True)
        if request.service_id == "obsidian-canvas-to-relationships":
            output_file = request.output_root / "relationships" / "relationships.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                json.dumps(_engine_payload("empty_relationships_output")),
                encoding="utf-8",
            )
            outputs = {"relationships": (output_file,)}
        elif request.service_id == "summarize-principles":
            output_file = request.output_root / "summary" / "principles-summary.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                json.dumps({"source": "principles", "summary": "Use clear principles."}),
                encoding="utf-8",
            )
            outputs = {"summary": (output_file,)}
        elif request.service_id == "summarize-jobs":
            output_file = request.output_root / "summary" / "jobs-summary.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                json.dumps({"source": "jobs", "summary": "Team needs clearer role shaping."}),
                encoding="utf-8",
            )
            outputs = {"summary": (output_file,)}
        elif request.service_id == "build-question-set":
            principles = json.loads(request.inputs["principles_summary"][0].read_text(encoding="utf-8"))
            jobs = json.loads(request.inputs["jobs_summary"][0].read_text(encoding="utf-8"))
            output_file = request.output_root / "questions" / "questions.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                json.dumps(
                    {
                        "sources": [principles["source"], jobs["source"]],
                        "questions": [
                            "How should the principles shape role design?",
                            "Where are the biggest role ambiguity risks?"
                        ],
                    }
                ),
                encoding="utf-8",
            )
            outputs = {"questions": (output_file,)}
        elif request.service_id == "build-invalid-question-set":
            output_file = request.output_root / "questions" / "questions.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                json.dumps(_engine_payload("invalid_questions_output")),
                encoding="utf-8",
            )
            outputs = {"questions": (output_file,)}
        elif request.service_id == "build-missing-output-port":
            outputs = {}
        elif request.service_id == "build-missing-output-file":
            output_file = request.output_root / "questions" / "questions.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            outputs = {"questions": (output_file,)}
        elif request.service_id == "split-principles":
            first_file = request.output_root / "documents" / "principle-1.md"
            second_file = request.output_root / "documents" / "principle-2.md"
            first_file.parent.mkdir(parents=True, exist_ok=True)
            first_file.write_text("# Principle 1\nClarity\n", encoding="utf-8")
            second_file.write_text("# Principle 2\nAlignment\n", encoding="utf-8")
            outputs = {"documents": (first_file, second_file)}
        elif request.service_id == "bundle-principles":
            summaries = [path.read_text(encoding="utf-8") for path in request.inputs["documents"]]
            output_file = request.output_root / "bundle" / "bundle.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                json.dumps(
                    {
                        "count": len(summaries),
                        "titles": [text.splitlines()[0] for text in summaries],
                    }
                ),
                encoding="utf-8",
            )
            outputs = {"bundle": (output_file,)}
        elif request.service_id == "bundle-directory-principles":
            merged_root = request.inputs["documents"][0]
            summaries = [path.read_text(encoding="utf-8") for path in sorted(merged_root.rglob("*.md"))]
            output_file = request.output_root / "bundle" / "bundle.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                json.dumps(
                    {
                        "count": len(summaries),
                        "titles": [text.splitlines()[0] for text in summaries],
                    }
                ),
                encoding="utf-8",
            )
            outputs = {"bundle": (output_file,)}
        elif request.service_id == "emit-collision-a":
            output_file = request.output_root / "documents" / "shared.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text("# Collision A\n", encoding="utf-8")
            outputs = {"documents": (output_file,)}
        elif request.service_id == "emit-collision-b":
            output_file = request.output_root / "documents" / "shared.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text("# Collision B\n", encoding="utf-8")
            outputs = {"documents": (output_file,)}
        elif request.service_id == "emit-directory-collision-a":
            output_dir = request.output_root / "documents" / "set-a"
            output_file = output_dir / "docs" / "shared.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text("# Directory Collision A\n", encoding="utf-8")
            outputs = {"documents": (output_dir,)}
        elif request.service_id == "emit-directory-collision-b":
            output_dir = request.output_root / "documents" / "set-b"
            output_file = output_dir / "docs" / "shared.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text("# Directory Collision B\n", encoding="utf-8")
            outputs = {"documents": (output_dir,)}
        else:
            raise AssertionError(f"Unexpected fake service id: {request.service_id}")
        request.log_path.parent.mkdir(parents=True, exist_ok=True)
        request.log_path.write_text("fake-runner ok", encoding="utf-8")
        return ServiceRunnerResult(outputs=outputs, exit_code=0)


class FailingServiceRunner(FakeServiceRunner):
    def run(self, request):
        if request.service_id == "build-failing-question-set":
            request.log_path.parent.mkdir(parents=True, exist_ok=True)
            request.log_path.write_text("failing-runner boom", encoding="utf-8")
            raise RuntimeError("simulated downstream failure")
        return super().run(request)


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
            input_canvas.write_text(json.dumps(_engine_payload("empty_canvas_input")), encoding="utf-8")

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
            self.assertEqual(
                json.loads(output_file.read_text(encoding="utf-8")),
                _engine_payload("empty_relationships_output"),
            )
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

    def test_load_runtime_config_preserves_service_environment_variables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_config_path = root / "runtime.json"
            runtime_config_path.write_text(
                json.dumps(
                    {
                        "runner": {
                            "kind": "docker",
                            "services": {
                                "json-to-json-llm-transformer": {
                                    "image": "linksmith-json-to-json-llm-transformer:test",
                                    "inputArguments": {
                                        "data": "--data",
                                        "prompt": "--prompt",
                                        "schema": "--schema",
                                    },
                                    "outputDirArgument": "--output-dir",
                                    "environment": {
                                        "LINKSMITH_LLM_BASE_URL": "http://host.docker.internal:1234/v1",
                                        "LINKSMITH_LLM_MODEL": "local-model",
                                    },
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            runtime_config = load_runtime_config(runtime_config_path, validate_schema=False)
            runner = load_service_runner(runtime_config)

            self.assertIsInstance(runner, DockerServiceRunner)
            config = runner._service_configs["json-to-json-llm-transformer"]
            self.assertEqual(
                config.environment["LINKSMITH_LLM_BASE_URL"],
                "http://host.docker.internal:1234/v1",
            )
            self.assertEqual(config.environment["LINKSMITH_LLM_MODEL"], "local-model")

    def test_run_pipeline_routes_multiple_invocations_into_downstream_service(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            principles_file = root / "principles.md"
            jobs_file = root / "jobs.md"
            registry_path.write_text(json.dumps(_multi_service_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_multi_service_pipeline_payload()), encoding="utf-8")
            principles_file.write_text("# Principles\n- Clarity matters\n", encoding="utf-8")
            jobs_file.write_text("# Roles\n- Delivery lead\n", encoding="utf-8")

            result = run_pipeline(
                PipelineRunRequest(
                    pipeline_path=pipeline_path,
                    registry_path=registry_path,
                    pipeline_inputs={
                        "principles": principles_file,
                        "jobs": jobs_file,
                    },
                    run_root=root / "runs",
                    service_runner=FakeServiceRunner(),
                    run_id="run-multi-001",
                    validate_schema=False,
                )
            )

            output_file = result.outputs["questions"][0]
            payload = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["sources"], ["principles", "jobs"])
            self.assertEqual(len(payload["questions"]), 2)
            self.assertEqual(len(result.invocation_manifests), 3)

    def test_run_pipeline_rejects_invalid_json_output_against_declared_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            principles_file = root / "principles.md"
            jobs_file = root / "jobs.md"
            registry_path.write_text(
                json.dumps(_invalid_output_registry_payload(_questions_schema_path())),
                encoding="utf-8",
            )
            pipeline_path.write_text(json.dumps(_invalid_output_pipeline_payload()), encoding="utf-8")
            principles_file.write_text("# Principles\n- Clarity matters\n", encoding="utf-8")
            jobs_file.write_text("# Roles\n- Delivery lead\n", encoding="utf-8")

            with self.assertRaises(SchemaValidationError):
                run_pipeline(
                    PipelineRunRequest(
                        pipeline_path=pipeline_path,
                        registry_path=registry_path,
                        pipeline_inputs={
                            "principles": principles_file,
                            "jobs": jobs_file,
                        },
                        run_root=root / "runs",
                        service_runner=FakeServiceRunner(),
                        run_id="run-invalid-001",
                        validate_schema=False,
                        validate_outputs=True,
                    )
                )

    def test_run_pipeline_rejects_missing_declared_output_port(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            principles_file = root / "principles.md"
            jobs_file = root / "jobs.md"
            registry_path.write_text(
                json.dumps(_missing_output_port_registry_payload()),
                encoding="utf-8",
            )
            pipeline_path.write_text(json.dumps(_missing_output_port_pipeline_payload()), encoding="utf-8")
            principles_file.write_text("# Principles\n- Clarity matters\n", encoding="utf-8")
            jobs_file.write_text("# Roles\n- Delivery lead\n", encoding="utf-8")

            with self.assertRaisesRegex(ConfigurationError, "did not produce declared output port 'questions'"):
                run_pipeline(
                    PipelineRunRequest(
                        pipeline_path=pipeline_path,
                        registry_path=registry_path,
                        pipeline_inputs={
                            "principles": principles_file,
                            "jobs": jobs_file,
                        },
                        run_root=root / "runs",
                        service_runner=FakeServiceRunner(),
                        run_id="run-missing-port-001",
                        validate_schema=False,
                    )
                )

    def test_run_pipeline_rejects_missing_declared_output_artifact_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            principles_file = root / "principles.md"
            jobs_file = root / "jobs.md"
            registry_path.write_text(
                json.dumps(_missing_output_file_registry_payload()),
                encoding="utf-8",
            )
            pipeline_path.write_text(json.dumps(_missing_output_file_pipeline_payload()), encoding="utf-8")
            principles_file.write_text("# Principles\n- Clarity matters\n", encoding="utf-8")
            jobs_file.write_text("# Roles\n- Delivery lead\n", encoding="utf-8")

            with self.assertRaisesRegex(ConfigurationError, "does not exist"):
                run_pipeline(
                    PipelineRunRequest(
                        pipeline_path=pipeline_path,
                        registry_path=registry_path,
                        pipeline_inputs={
                            "principles": principles_file,
                            "jobs": jobs_file,
                        },
                        run_root=root / "runs",
                        service_runner=FakeServiceRunner(),
                        run_id="run-missing-file-001",
                        validate_schema=False,
                    )
                )

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

    def test_docker_service_runner_mounts_many_file_input_as_port_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_root = root / "inputs" / "documents"
            first_file = input_root / "principle-1.md"
            second_file = input_root / "principle-2.md"
            output_root = root / "outputs"
            log_path = root / "runner.log"
            input_root.mkdir(parents=True, exist_ok=True)
            first_file.write_text("# One\n", encoding="utf-8")
            second_file.write_text("# Two\n", encoding="utf-8")

            request = ServiceRunnerRequest(
                step_id="bundle",
                invocation_id="all",
                service_id="bundle-principles",
                inputs={"documents": (first_file, second_file)},
                input_contracts={
                    "documents": PortContract(
                        name="documents",
                        type="markdown-document",
                        mode="file",
                        cardinality="many",
                    )
                },
                output_contracts={
                    "bundle": PortContract(
                        name="bundle",
                        type="summary-json",
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
                    "bundle-principles": DockerServiceConfig(
                        image="example-image:latest",
                        input_arguments={"documents": "--documents"},
                        output_dir_argument="--output-dir",
                        output_file_name_arguments={"bundle": "--output-file-name"},
                        output_file_names={"bundle": "bundle.json"},
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
            self.assertIn(f"{input_root}:/data/inputs/documents:ro", command)
            self.assertIn("--documents", command)
            self.assertIn("/data/inputs/documents", command)

    def test_docker_service_runner_injects_environment_variables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_file = root / "input.json"
            output_root = root / "outputs"
            log_path = root / "runner.log"
            input_file.write_text("{}", encoding="utf-8")

            request = ServiceRunnerRequest(
                step_id="transform",
                invocation_id="summary",
                service_id="json-to-json-llm-transformer",
                inputs={"data": (input_file,)},
                input_contracts={
                    "data": PortContract(
                        name="data",
                        type="json-document",
                        mode="file",
                        cardinality="one",
                    )
                },
                output_contracts={
                    "result": PortContract(
                        name="result",
                        type="json-document",
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
                    "json-to-json-llm-transformer": DockerServiceConfig(
                        image="example-image:latest",
                        input_arguments={"data": "--data"},
                        output_dir_argument="--output-dir",
                        output_file_name_arguments={"result": "--output-file-name"},
                        output_file_names={"result": "result.json"},
                        input_mount_root="/data/inputs",
                        output_mount_root="/data/output",
                        environment={
                            "LINKSMITH_LLM_BASE_URL": "http://host.docker.internal:1234/v1",
                            "LINKSMITH_LLM_MODEL": "local-model",
                        },
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
            self.assertIn("-e", command)
            self.assertIn(
                "LINKSMITH_LLM_BASE_URL=http://host.docker.internal:1234/v1",
                command,
            )
            self.assertIn("LINKSMITH_LLM_MODEL=local-model", command)

    def test_run_pipeline_writes_failed_manifests_for_downstream_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            principles_file = root / "principles.md"
            jobs_file = root / "jobs.md"
            registry_path.write_text(json.dumps(_failing_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_failing_pipeline_payload()), encoding="utf-8")
            principles_file.write_text("# Principles\n- Clarity matters\n", encoding="utf-8")
            jobs_file.write_text("# Roles\n- Delivery lead\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "simulated downstream failure"):
                run_pipeline(
                    PipelineRunRequest(
                        pipeline_path=pipeline_path,
                        registry_path=registry_path,
                        pipeline_inputs={
                            "principles": principles_file,
                            "jobs": jobs_file,
                        },
                        run_root=root / "runs",
                        service_runner=FailingServiceRunner(),
                        run_id="run-failure-001",
                        validate_schema=False,
                    )
                )

            run_manifest = json.loads((root / "runs" / "run-failure-001" / "manifests" / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(run_manifest["status"], "failed")
            self.assertIn("simulated downstream failure", run_manifest["error"])
            self.assertEqual(run_manifest["outputs"], {})
            self.assertEqual(len(run_manifest["invocationManifests"]), 3)

            upstream_manifest = json.loads(
                (root / "runs" / "run-failure-001" / "manifests" / "invocations" / "summaries.principles.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(upstream_manifest["status"], "succeeded")

            failed_manifest = json.loads(
                (root / "runs" / "run-failure-001" / "manifests" / "invocations" / "questioning.combine.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(failed_manifest["status"], "failed")
            self.assertIn("simulated downstream failure", failed_manifest["error"])
            self.assertEqual(failed_manifest["outputs"], {})

    def test_semantic_validation_rejects_many_to_one_file_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            registry_path.write_text(json.dumps(_many_services_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_invalid_many_to_one_pipeline_payload()), encoding="utf-8")

            registry = load_registry_document(registry_path, validate_schema=False)
            pipeline = load_pipeline_definition(pipeline_path, validate_schema=False)

            with self.assertRaises(PipelineValidationError):
                validate_pipeline_semantics(pipeline, registry)

    def test_semantic_validation_rejects_missing_required_invocation_input_and_pipeline_output_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            registry_path.write_text(json.dumps(_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_missing_edge_pipeline_payload()), encoding="utf-8")

            registry = load_registry_document(registry_path, validate_schema=False)
            pipeline = load_pipeline_definition(pipeline_path, validate_schema=False)

            with self.assertRaises(PipelineValidationError) as context:
                validate_pipeline_semantics(pipeline, registry)

            self.assertTrue(any("must have an incoming edge" in error for error in context.exception.errors))

    def test_run_pipeline_rejects_multiple_artifacts_for_single_pipeline_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            first_input = root / "input-1.canvas"
            second_input = root / "input-2.canvas"
            registry_path.write_text(json.dumps(_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_pipeline_payload()), encoding="utf-8")
            first_input.write_text("{}", encoding="utf-8")
            second_input.write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(ConfigurationError, "expects one source artifact"):
                run_pipeline(
                    PipelineRunRequest(
                        pipeline_path=pipeline_path,
                        registry_path=registry_path,
                        pipeline_inputs={"canvas": (first_input, second_input)},
                        run_root=root / "runs",
                        service_runner=FakeServiceRunner(),
                        validate_schema=False,
                    )
                )

    def test_run_pipeline_rejects_directory_for_file_pipeline_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            input_dir = root / "canvas-dir"
            registry_path.write_text(json.dumps(_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_pipeline_payload()), encoding="utf-8")
            input_dir.mkdir(parents=True, exist_ok=True)

            with self.assertRaisesRegex(ConfigurationError, "expects file artifacts"):
                run_pipeline(
                    PipelineRunRequest(
                        pipeline_path=pipeline_path,
                        registry_path=registry_path,
                        pipeline_inputs={"canvas": input_dir},
                        run_root=root / "runs",
                        service_runner=FakeServiceRunner(),
                        validate_schema=False,
                    )
                )

    def test_run_pipeline_routes_many_file_artifacts_into_many_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            principles_file = root / "principles.md"
            registry_path.write_text(json.dumps(_many_services_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_many_pipeline_payload()), encoding="utf-8")
            principles_file.write_text("# Principles\n- Clarity matters\n", encoding="utf-8")

            result = run_pipeline(
                PipelineRunRequest(
                    pipeline_path=pipeline_path,
                    registry_path=registry_path,
                    pipeline_inputs={"principles": principles_file},
                    run_root=root / "runs",
                    service_runner=FakeServiceRunner(),
                    run_id="run-many-001",
                    validate_schema=False,
                )
            )

            output_file = result.outputs["bundle"][0]
            payload = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["count"], 2)
            self.assertEqual(payload["titles"], ["# Principle 1", "# Principle 2"])

    def test_run_pipeline_rejects_many_file_name_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            trigger_file = root / "trigger.md"
            registry_path.write_text(json.dumps(_collision_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_collision_pipeline_payload()), encoding="utf-8")
            trigger_file.write_text("# Trigger\n", encoding="utf-8")

            with self.assertRaisesRegex(ConfigurationError, "Filename collision"):
                run_pipeline(
                    PipelineRunRequest(
                        pipeline_path=pipeline_path,
                        registry_path=registry_path,
                        pipeline_inputs={"trigger": trigger_file},
                        run_root=root / "runs",
                        service_runner=FakeServiceRunner(),
                        run_id="run-collision-001",
                        validate_schema=False,
                    )
                )

    def test_run_pipeline_rejects_directory_merge_relative_path_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry_path = root / "registry.json"
            pipeline_path = root / "pipeline.json"
            trigger_file = root / "trigger.md"
            registry_path.write_text(json.dumps(_directory_collision_registry_payload()), encoding="utf-8")
            pipeline_path.write_text(json.dumps(_directory_collision_pipeline_payload()), encoding="utf-8")
            trigger_file.write_text("# Trigger\n", encoding="utf-8")

            with self.assertRaisesRegex(ConfigurationError, "Relative path collision"):
                run_pipeline(
                    PipelineRunRequest(
                        pipeline_path=pipeline_path,
                        registry_path=registry_path,
                        pipeline_inputs={"trigger": trigger_file},
                        run_root=root / "runs",
                        service_runner=FakeServiceRunner(),
                        run_id="run-directory-collision-001",
                        validate_schema=False,
                    )
                )


def _registry_payload() -> dict[str, object]:
    return _engine_payload("registry_payload")


def _pipeline_payload() -> dict[str, object]:
    return _engine_payload("pipeline_payload")


def _missing_edge_pipeline_payload() -> dict[str, object]:
    return _engine_payload("missing_edge_pipeline_payload")


def _runtime_payload() -> dict[str, object]:
    return _engine_payload("runtime_payload")


def _multi_service_registry_payload() -> dict[str, object]:
    return _engine_payload("multi_service_registry_payload")


def _multi_service_pipeline_payload() -> dict[str, object]:
    return _engine_payload("multi_service_pipeline_payload")


def _invalid_output_registry_payload(questions_schema_path: str) -> dict[str, object]:
    return _engine_payload(
        "invalid_output_registry_payload",
        substitutions={"QUESTIONS_SCHEMA_PATH": questions_schema_path},
    )


def _invalid_output_pipeline_payload() -> dict[str, object]:
    return _engine_payload("invalid_output_pipeline_payload")


def _missing_output_port_registry_payload() -> dict[str, object]:
    return _engine_payload("missing_output_port_registry_payload")


def _missing_output_port_pipeline_payload() -> dict[str, object]:
    return _engine_payload("missing_output_port_pipeline_payload")


def _missing_output_file_registry_payload() -> dict[str, object]:
    return _engine_payload("missing_output_file_registry_payload")


def _missing_output_file_pipeline_payload() -> dict[str, object]:
    return _engine_payload("missing_output_file_pipeline_payload")


def _questions_schema_path() -> str:
    return str((Path(__file__).resolve().parents[1] / "schemas" / "questions.schema.json").resolve())


def _failing_registry_payload() -> dict[str, object]:
    return _engine_payload("failing_registry_payload")


def _failing_pipeline_payload() -> dict[str, object]:
    return _engine_payload("failing_pipeline_payload")


def _many_services_registry_payload() -> dict[str, object]:
    return _engine_payload("many_services_registry_payload")


def _many_pipeline_payload() -> dict[str, object]:
    return _engine_payload("many_pipeline_payload")


def _invalid_many_to_one_pipeline_payload() -> dict[str, object]:
    return _engine_payload("invalid_many_to_one_pipeline_payload")


def _collision_registry_payload() -> dict[str, object]:
    return _engine_payload("collision_registry_payload")


def _collision_pipeline_payload() -> dict[str, object]:
    return _engine_payload("collision_pipeline_payload")


def _directory_collision_registry_payload() -> dict[str, object]:
    return _engine_payload("directory_collision_registry_payload")


def _directory_collision_pipeline_payload() -> dict[str, object]:
    return _engine_payload("directory_collision_pipeline_payload")


if __name__ == "__main__":
    unittest.main()
