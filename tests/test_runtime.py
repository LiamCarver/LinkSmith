from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path, PurePath
from unittest.mock import patch

from linksmith_core.errors import ConfigurationError, SchemaDependencyError
from linksmith_core.models import (
    JsonOutput,
    MarkdownOutput,
    MarkdownDirectoryOutput,
    MarkdownDocument,
    PortContract,
    ServiceContract,
    ServiceRunRequest,
)
from linksmith_core.runtime import run_service
from linksmith_core.schemas import SchemaValidator
from tests.json_fixtures import load_fixture_json


def _runtime_payload(name: str):
    return load_fixture_json("runtime/payloads.json", key=name)


class EchoService:
    contract = ServiceContract(
        service_id="echo-service",
        inputs=(
            PortContract(name="source", type="json", mode="file", cardinality="one"),
        ),
        outputs=(
            PortContract(name="result", type="json", mode="file", cardinality="one"),
        ),
    )

    def execute(self, inputs, context):
        source = inputs["source"][0]
        context.metadata["input_path"] = str(source.path)
        return {
            "result": JsonOutput(
                relative_path=PurePath("result.json"),
                data={"copied": source.data["value"]},
            )
        }


class DirectorySummaryService:
    contract = ServiceContract(
        service_id="directory-summary",
        inputs=(
            PortContract(name="notes", type="markdown", mode="directory", cardinality="one"),
        ),
        outputs=(
            PortContract(name="rendered", type="markdown", mode="directory", cardinality="one"),
        ),
    )

    def execute(self, inputs, context):
        directory = inputs["notes"][0]
        names = [doc.relative_path.as_posix() for doc in directory.documents]
        return {
            "rendered": MarkdownDirectoryOutput(
                relative_path=PurePath("summary"),
                documents=(
                    MarkdownDocument(
                        relative_path=PurePath("index.md"),
                        text="\n".join(names),
                    ),
                ),
            )
        }


class RuntimeTests(unittest.TestCase):
    def test_run_service_loads_json_and_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_file = root / "input.json"
            input_file.write_text(json.dumps(_runtime_payload("echo_input")), encoding="utf-8")
            output_root = root / "out"

            result = run_service(
                EchoService(),
                ServiceRunRequest(inputs={"source": input_file}, output_root=output_root),
            )

            output_file = output_root / "result" / "result.json"
            self.assertTrue(output_file.exists())
            self.assertEqual(
                json.loads(output_file.read_text(encoding="utf-8")),
                _runtime_payload("echo_output"),
            )
            self.assertEqual(result.service_name, "echo-service")
            self.assertTrue(any(entry.stage == "load" for entry in result.logs))

    def test_directory_inputs_are_normalized_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "notes"
            nested = source_dir / "nested"
            nested.mkdir(parents=True)
            (source_dir / "a.md").write_text("# A", encoding="utf-8")
            (nested / "b.md").write_text("# B", encoding="utf-8")
            output_root = root / "out"

            run_service(
                DirectorySummaryService(),
                ServiceRunRequest(inputs={"notes": source_dir}, output_root=output_root),
            )

            summary_file = output_root / "rendered" / "summary" / "index.md"
            self.assertEqual(
                summary_file.read_text(encoding="utf-8"),
                "a.md\nnested/b.md",
            )

    def test_missing_required_port_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(ConfigurationError):
                run_service(
                    EchoService(),
                    ServiceRunRequest(inputs={}, output_root=root / "out"),
                )

    def test_schema_validation_requires_dependency(self) -> None:
        validator = SchemaValidator(base_dir=Path("."))
        with patch("linksmith_core.schemas.importlib.util.find_spec", return_value=None):
            with self.assertRaises(SchemaDependencyError):
                validator.validate({"a": 1}, "schemas/registry.schema.json")

    def test_custom_semantic_json_types_are_supported(self) -> None:
        class SemanticJsonService:
            contract = ServiceContract(
                service_id="semantic-json-service",
                inputs=(
                    PortContract(
                        name="canvas",
                        type="obsidian-canvas",
                        mode="file",
                        cardinality="one",
                    ),
                ),
                outputs=(
                    PortContract(
                        name="relationships",
                        type="canvas-relationships",
                        mode="file",
                        cardinality="one",
                    ),
                ),
            )

            def execute(self, inputs, context):
                return {
                    "relationships": JsonOutput(
                        relative_path=PurePath("relationships.json"),
                        data=_runtime_payload("empty_relationships_output"),
                    )
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_file = root / "input.canvas"
            input_file.write_text(json.dumps(_runtime_payload("empty_canvas_input")), encoding="utf-8")
            result = run_service(
                SemanticJsonService(),
                ServiceRunRequest(
                    inputs={"canvas": input_file},
                    output_root=root / "out",
                ),
            )
            output_file = root / "out" / "relationships" / "relationships.json"
            self.assertTrue(output_file.exists())
            self.assertEqual(result.written_outputs["relationships"], (output_file,))

    def test_output_type_mismatch_raises(self) -> None:
        class InvalidOutputService:
            contract = ServiceContract(
                service_id="invalid-output-service",
                inputs=(
                    PortContract(name="source", type="json", mode="file", cardinality="one"),
                ),
                outputs=(
                    PortContract(name="result", type="json", mode="file", cardinality="one"),
                ),
            )

            def execute(self, inputs, context):
                return {
                    "result": MarkdownOutput(
                        relative_path=PurePath("result.md"),
                        text="not json",
                    )
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_file = root / "input.json"
            input_file.write_text(json.dumps(_runtime_payload("echo_input")), encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                run_service(
                    InvalidOutputService(),
                    ServiceRunRequest(inputs={"source": input_file}, output_root=root / "out"),
                )

    def test_optional_output_can_be_omitted(self) -> None:
        class OptionalOutputService:
            contract = ServiceContract(
                service_id="optional-output-service",
                inputs=(
                    PortContract(name="source", type="json", mode="file", cardinality="one"),
                ),
                outputs=(
                    PortContract(
                        name="result",
                        type="json",
                        mode="file",
                        cardinality="one",
                        required=False,
                    ),
                ),
            )

            def execute(self, inputs, context):
                return {}

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_file = root / "input.json"
            input_file.write_text(json.dumps(_runtime_payload("echo_input")), encoding="utf-8")
            result = run_service(
                OptionalOutputService(),
                ServiceRunRequest(inputs={"source": input_file}, output_root=root / "out"),
            )
            self.assertEqual(result.written_outputs["result"], tuple())

    def test_required_many_output_cannot_be_empty(self) -> None:
        class EmptyManyOutputService:
            contract = ServiceContract(
                service_id="empty-many-output-service",
                inputs=(
                    PortContract(name="source", type="json", mode="file", cardinality="one"),
                ),
                outputs=(
                    PortContract(name="result", type="json", mode="file", cardinality="many"),
                ),
            )

            def execute(self, inputs, context):
                return {"result": tuple()}

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_file = root / "input.json"
            input_file.write_text(json.dumps(_runtime_payload("echo_input")), encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                run_service(
                    EmptyManyOutputService(),
                    ServiceRunRequest(inputs={"source": input_file}, output_root=root / "out"),
                )


if __name__ == "__main__":
    unittest.main()
