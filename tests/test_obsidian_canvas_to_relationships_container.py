from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class ObsidianCanvasContainerTests(unittest.TestCase):
    def test_container_converts_canvas_fixture_to_expected_json(self) -> None:
        if shutil.which("docker") is None:
            self.skipTest("Docker is not available in PATH.")

        repo_root = Path(__file__).resolve().parents[1]
        fixture_root = repo_root / "examples" / "services" / "obsidian-canvas-to-relationships"
        image_tag = "linksmith-obsidian-canvas-to-relationships:test"

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
            temp_root = Path(temp_dir)
            output_dir = temp_root / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            input_file = fixture_root / "input" / "realistic-nested.canvas"

            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{input_file}:/data/input.canvas:ro",
                    "-v",
                    f"{output_dir}:/data/output",
                    "-v",
                    f"{repo_root / 'schemas'}:/app/schemas:ro",
                    image_tag,
                    "--input",
                    "/data/input.canvas",
                    "--output-dir",
                    "/data/output",
                    "--output-file-name",
                    "relationships.json",
                    "--schema-base-dir",
                    "/app",
                ],
                check=True,
            )

            actual_path = output_dir / "relationships" / "relationships.json"
            expected_path = fixture_root / "expected" / "realistic-nested.relationships.json"
            actual = json.loads(actual_path.read_text(encoding="utf-8"))
            expected = json.loads(expected_path.read_text(encoding="utf-8"))

            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
