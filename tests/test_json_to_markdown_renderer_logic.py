from __future__ import annotations

import json
import unittest
from pathlib import Path

from linksmith_core.errors import ConfigurationError
from linksmith_services.json_to_markdown_renderer import render_markdown_document
from tests.json_fixtures import load_fixture_json


def _logic_payload(name: str):
    return load_fixture_json("json-to-markdown-renderer-logic/payloads.json", key=name)


class JsonToMarkdownRendererLogicTests(unittest.TestCase):
    def test_basic_report_fixture_renders_to_expected_markdown(self) -> None:
        fixture_dir = Path(__file__).resolve().parents[1] / "fixtures" / "services" / "json-to-markdown-renderer"
        data_path = fixture_dir / "input" / "basic-report.data.json"
        template_path = fixture_dir / "input" / "basic-report.template.mustache"
        expected_path = fixture_dir / "expected" / "basic-report.document.md"

        payload = json.loads(data_path.read_text(encoding="utf-8"))
        template = template_path.read_text(encoding="utf-8")
        expected = expected_path.read_text(encoding="utf-8")

        actual = render_markdown_document(payload, template)

        self.assertEqual(actual, expected)

    def test_render_rejects_missing_template_key(self) -> None:
        payload = _logic_payload("only_title")
        template = "# {{title}}\n\n{{summary}}\n"

        with self.assertRaisesRegex(ConfigurationError, "missing key 'summary'"):
            render_markdown_document(payload, template)

    def test_render_allows_inverted_section_for_absent_key(self) -> None:
        payload = _logic_payload("only_title")
        template = "# {{title}}\n\n{{^summary}}No summary{{/summary}}\n"

        actual = render_markdown_document(payload, template)

        self.assertEqual(actual, "# Only Title\n\nNo summary\n")

    def test_render_allows_falsey_section_value_without_descending(self) -> None:
        payload = _logic_payload("only_title_owner_null")
        template = "# {{title}}\n{{#owner}}{{name}}{{/owner}}"

        actual = render_markdown_document(payload, template)

        self.assertEqual(actual, "# Only Title\n")

    def test_render_allows_truthy_scalar_section_value(self) -> None:
        payload = _logic_payload("only_title_show_title")
        template = "{{#show_title}}{{title}}{{/show_title}}"

        actual = render_markdown_document(payload, template)

        self.assertEqual(actual, "Only Title")


if __name__ == "__main__":
    unittest.main()
