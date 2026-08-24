from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path, PurePath

from linksmith_core.errors import ConfigurationError
from linksmith_services.markdown_directory_to_json_corpus import SourceMarkdownDocument, build_markdown_corpus


class MarkdownDirectoryToJsonCorpusLogicTests(unittest.TestCase):
    def test_realistic_fixture_builds_expected_corpus(self) -> None:
        fixture_root = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "services"
            / "markdown-directory-to-json-corpus"
        )
        input_root = fixture_root / "input" / "documents"
        expected_path = fixture_root / "expected" / "corpus.json"

        documents = [
            SourceMarkdownDocument(
                relative_path=PurePath(path.relative_to(input_root).as_posix()),
                text=path.read_text(encoding="utf-8"),
            )
            for path in sorted(input_root.rglob("*.md"))
            if path.is_file()
        ]
        expected = json.loads(expected_path.read_text(encoding="utf-8"))

        actual = build_markdown_corpus(documents)

        self.assertEqual(actual, expected)

    def test_build_orders_items_by_relative_path(self) -> None:
        actual = build_markdown_corpus(
            [
                SourceMarkdownDocument(relative_path=PurePath("zeta.md"), text="# Zeta\n"),
                SourceMarkdownDocument(relative_path=PurePath("alpha.md"), text="# Alpha\n"),
            ]
        )

        self.assertEqual(
            [item["sourceId"] for item in actual["items"]],
            ["001-alpha", "002-zeta"],
        )

    def test_build_rejects_empty_inputs(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "at least one"):
            build_markdown_corpus([])

    def test_build_rejects_blank_markdown_content(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "must not be empty"):
            build_markdown_corpus(
                [SourceMarkdownDocument(relative_path=PurePath("empty.md"), text="   ")]
            )


if __name__ == "__main__":
    unittest.main()
