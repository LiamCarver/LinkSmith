from __future__ import annotations

import json
import unittest
from pathlib import PurePath

from linksmith_core.errors import ConfigurationError
from linksmith_services.json_files_to_json_bundle import SourceJsonDocument, bundle_json_documents


class JsonFilesToJsonBundleLogicTests(unittest.TestCase):
    def test_realistic_fixture_bundles_to_expected_json(self) -> None:
        fixture_root = (
            __import__("pathlib").Path(__file__).resolve().parents[1]
            / "fixtures"
            / "services"
            / "json-files-to-json-bundle"
        )
        input_root = fixture_root / "input" / "documents"
        expected_path = fixture_root / "expected" / "bundle.json"

        documents = [
            SourceJsonDocument(
                relative_path=PurePath(path.relative_to(input_root).as_posix()),
                data=json.loads(path.read_text(encoding="utf-8")),
            )
            for path in sorted(input_root.rglob("*"))
            if path.is_file()
        ]
        expected = json.loads(expected_path.read_text(encoding="utf-8"))

        actual = bundle_json_documents(documents)

        self.assertEqual(actual, expected)

    def test_bundle_orders_items_by_relative_path(self) -> None:
        actual = bundle_json_documents(
            [
                SourceJsonDocument(relative_path=PurePath("zeta.json"), data={"value": 2}),
                SourceJsonDocument(relative_path=PurePath("alpha.json"), data={"value": 1}),
            ]
        )

        self.assertEqual(
            [item["sourceId"] for item in actual["items"]],
            ["001-alpha", "002-zeta"],
        )

    def test_bundle_rejects_empty_inputs(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "at least one"):
            bundle_json_documents([])


if __name__ == "__main__":
    unittest.main()
