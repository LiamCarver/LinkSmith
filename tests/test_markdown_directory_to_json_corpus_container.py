from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class MarkdownDirectoryToJsonCorpusContainerTests(unittest.TestCase):
    def test_container_reads_markdown_directory_to_expected_corpus(self) -> None:
        if shutil.which("docker") is None:
            self.skipTest("Docker is not available in PATH.")

        repo_root = Path(__file__).resolve().parents[1]
        fixture_root = repo_root / "fixtures" / "services" / "markdown-directory-to-json-corpus"
        image_tag = "linksmith-markdown-directory-to-json-corpus:test"

        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                str(repo_root / "services" / "markdown-directory-to-json-corpus" / "Dockerfile"),
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
            documents_dir = fixture_root / "input" / "documents"

            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{documents_dir}:/data/documents:ro",
                    "-v",
                    f"{output_dir}:/data/output",
                    image_tag,
                    "--documents-dir",
                    "/data/documents",
                    "--output-dir",
                    "/data/output",
                    "--output-file-name",
                    "corpus.json",
                    "--schema-base-dir",
                    "/app",
                ],
                check=True,
            )

            actual_path = output_dir / "corpus" / "corpus.json"
            expected_path = fixture_root / "expected" / "corpus.json"
            actual = json.loads(actual_path.read_text(encoding="utf-8"))
            expected = json.loads(expected_path.read_text(encoding="utf-8"))

            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
