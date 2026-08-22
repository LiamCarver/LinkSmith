from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class JsonToMarkdownRendererContainerTests(unittest.TestCase):
    def test_container_renders_fixture_to_expected_markdown(self) -> None:
        if shutil.which("docker") is None:
            self.skipTest("Docker is not available in PATH.")

        repo_root = Path(__file__).resolve().parents[1]
        fixture_root = repo_root / "fixtures" / "services" / "json-to-markdown-renderer"
        image_tag = "linksmith-json-to-markdown-renderer:test"

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
            temp_root = Path(temp_dir)
            output_dir = temp_root / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            data_file = fixture_root / "input" / "basic-report.data.json"
            template_file = fixture_root / "input" / "basic-report.template.mustache"

            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{data_file}:/data/data.json:ro",
                    "-v",
                    f"{template_file}:/data/template.mustache:ro",
                    "-v",
                    f"{output_dir}:/data/output",
                    image_tag,
                    "--data",
                    "/data/data.json",
                    "--template",
                    "/data/template.mustache",
                    "--output-dir",
                    "/data/output",
                    "--output-file-name",
                    "document.md",
                ],
                check=True,
            )

            actual_path = output_dir / "document" / "document.md"
            expected_path = fixture_root / "expected" / "basic-report.document.md"
            actual = actual_path.read_text(encoding="utf-8")
            expected = expected_path.read_text(encoding="utf-8")

            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
