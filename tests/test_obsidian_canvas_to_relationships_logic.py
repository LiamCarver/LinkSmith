from __future__ import annotations

import json
import unittest
from pathlib import Path

from linksmith_services.obsidian_canvas_to_relationships import (
    convert_canvas_document,
)


class ObsidianCanvasLogicTests(unittest.TestCase):
    def test_realistic_nested_fixture_converts_to_expected_structure(self) -> None:
        fixture_dir = Path(__file__).resolve().parents[1] / "fixtures" / "services" / "obsidian-canvas-to-relationships"
        input_path = fixture_dir / "input" / "realistic-nested.canvas"
        expected_path = fixture_dir / "expected" / "realistic-nested.relationships.json"

        canvas_payload = json.loads(input_path.read_text(encoding="utf-8"))
        expected_payload = json.loads(expected_path.read_text(encoding="utf-8"))

        actual_payload = convert_canvas_document(canvas_payload)

        self.assertEqual(actual_payload, expected_payload)


if __name__ == "__main__":
    unittest.main()
