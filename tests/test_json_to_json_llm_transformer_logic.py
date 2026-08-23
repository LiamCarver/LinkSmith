from __future__ import annotations

import json
import unittest
from pathlib import Path

from linksmith_core.errors import ConfigurationError
from linksmith_services.json_to_json_llm_transformer import extract_json_object, render_prompt, transform_json_document


class FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def complete(self, *, model: str, messages: list[dict[str, str]], temperature: float) -> str:
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
        )
        return self._responses.pop(0)


class JsonToJsonLlmTransformerLogicTests(unittest.TestCase):
    def test_transform_fixture_renders_and_validates_expected_json(self) -> None:
        fixture_dir = Path(__file__).resolve().parents[1] / "fixtures" / "services" / "json-to-json-llm-transformer"
        payload = json.loads((fixture_dir / "input" / "minimal.data.json").read_text(encoding="utf-8"))
        prompt = (fixture_dir / "input" / "minimal.prompt.mustache").read_text(encoding="utf-8")
        schema = json.loads((fixture_dir / "input" / "minimal.schema.json").read_text(encoding="utf-8"))
        expected = json.loads((fixture_dir / "expected" / "minimal.result.json").read_text(encoding="utf-8"))
        client = FakeClient([json.dumps(expected)])

        actual = transform_json_document(
            payload,
            prompt,
            schema,
            client=client,
            model="local-model",
            temperature=0.0,
            max_retries=0,
        )

        self.assertEqual(actual, expected)
        self.assertEqual(client.calls[0]["model"], "local-model")
        self.assertIn("Release planning", client.calls[0]["messages"][1]["content"])

    def test_transform_retries_after_invalid_json_then_succeeds(self) -> None:
        payload = {"topic": "Planning", "source_notes": ["One"]}
        prompt = "Topic: {{input.topic}}\nSchema:\n{{output_schema_json}}"
        schema = {
            "type": "object",
            "required": ["title"],
            "properties": {"title": {"type": "string"}},
            "additionalProperties": False,
        }
        client = FakeClient(
            [
                "not json at all",
                '```json\n{"title":"Planning Summary"}\n```',
            ]
        )

        actual = transform_json_document(
            payload,
            prompt,
            schema,
            client=client,
            model="local-model",
            temperature=0.0,
            max_retries=1,
        )

        self.assertEqual(actual, {"title": "Planning Summary"})
        self.assertEqual(len(client.calls), 2)
        self.assertIn("invalid", client.calls[1]["messages"][-1]["content"].lower())

    def test_transform_rejects_schema_mismatch_after_retries(self) -> None:
        payload = {"topic": "Planning", "source_notes": ["One"]}
        prompt = "Topic: {{input.topic}}\nSchema:\n{{output_schema_json}}"
        schema = {
            "type": "object",
            "required": ["title"],
            "properties": {"title": {"type": "string"}},
            "additionalProperties": False,
        }
        client = FakeClient(['{"wrong":"shape"}', '{"wrong":"shape"}'])

        with self.assertRaisesRegex(RuntimeError, "did not satisfy the expected JSON contract"):
            transform_json_document(
                payload,
                prompt,
                schema,
                client=client,
                model="local-model",
                temperature=0.0,
                max_retries=1,
            )

    def test_extract_json_object_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "root must be an object"):
            extract_json_object("[1, 2, 3]")

    def test_render_prompt_exposes_schema_json(self) -> None:
        rendered = render_prompt(
            {"topic": "Planning"},
            "Topic: {{input.topic}}\n{{{output_schema_json}}}",
            {"type": "object"},
        )

        self.assertIn("Planning", rendered)
        self.assertIn('"type": "object"', rendered)


if __name__ == "__main__":
    unittest.main()
