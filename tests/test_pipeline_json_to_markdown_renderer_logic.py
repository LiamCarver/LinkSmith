from __future__ import annotations

import json
import unittest
from pathlib import Path

from linksmith_core.errors import ConfigurationError
from linksmith_services.pipeline_json_to_markdown_renderer import render_pipeline_document


class PipelineJsonToMarkdownRendererLogicTests(unittest.TestCase):
    def test_realistic_pipeline_fixture_renders_to_expected_markdown(self) -> None:
        fixture_dir = Path(__file__).resolve().parents[1] / "fixtures" / "services" / "pipeline-json-to-markdown-renderer"
        data_path = fixture_dir / "input" / "canvas-summary.pipeline.json"
        expected_path = fixture_dir / "expected" / "canvas-summary.document.md"

        payload = json.loads(data_path.read_text(encoding="utf-8"))
        expected = expected_path.read_text(encoding="utf-8")

        actual = render_pipeline_document(payload)

        self.assertEqual(actual, expected)

    def test_render_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "root must be an object"):
            render_pipeline_document(["not", "an", "object"])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
