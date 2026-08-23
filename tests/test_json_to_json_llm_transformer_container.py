from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class _FakeLlmHandler(BaseHTTPRequestHandler):
    response_body = {
        "choices": [
            {
                "message": {
                    "content": "```json\n{\"title\":\"Release planning Summary\",\"bullets\":[\"Need weekly cadence\",\"Clarify owners\"]}\n```"
                }
            }
        ]
    }
    requests: list[dict[str, object]] = []

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        self.__class__.requests.append(json.loads(body))
        payload = json.dumps(self.__class__.response_body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class JsonToJsonLlmTransformerContainerTests(unittest.TestCase):
    def test_container_transforms_fixture_to_expected_json(self) -> None:
        if shutil.which("docker") is None:
            self.skipTest("Docker is not available in PATH.")

        repo_root = Path(__file__).resolve().parents[1]
        fixture_root = repo_root / "fixtures" / "services" / "json-to-json-llm-transformer"
        image_tag = "linksmith-json-to-json-llm-transformer:test"

        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                str(repo_root / "services" / "json-to-json-llm-transformer" / "Dockerfile"),
                "-t",
                image_tag,
                str(repo_root),
            ],
            check=True,
        )

        _FakeLlmHandler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeLlmHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        self.addCleanup(server_thread.join, 1)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            output_dir = temp_root / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            data_file = fixture_root / "input" / "minimal.data.json"
            prompt_file = fixture_root / "input" / "minimal.prompt.mustache"
            schema_file = fixture_root / "input" / "minimal.schema.json"

            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--add-host",
                    "host.docker.internal:host-gateway",
                    "-v",
                    f"{data_file}:/data/data.json:ro",
                    "-v",
                    f"{prompt_file}:/data/prompt.mustache:ro",
                    "-v",
                    f"{schema_file}:/data/schema.json:ro",
                    "-v",
                    f"{output_dir}:/data/output",
                    image_tag,
                    "--data",
                    "/data/data.json",
                    "--prompt",
                    "/data/prompt.mustache",
                    "--schema",
                    "/data/schema.json",
                    "--base-url",
                    f"http://host.docker.internal:{server.server_port}/v1",
                    "--api-key",
                    "test-key",
                    "--model",
                    "fake-local-model",
                    "--max-retries",
                    "1",
                    "--output-dir",
                    "/data/output",
                    "--output-file-name",
                    "result.json",
                ],
                check=True,
            )

            actual_path = output_dir / "result" / "result.json"
            expected_path = fixture_root / "expected" / "minimal.result.json"
            actual = json.loads(actual_path.read_text(encoding="utf-8"))
            expected = json.loads(expected_path.read_text(encoding="utf-8"))

            self.assertEqual(actual, expected)
            self.assertEqual(_FakeLlmHandler.requests[0]["model"], "fake-local-model")
            self.assertIn("Release planning", _FakeLlmHandler.requests[0]["messages"][1]["content"])


if __name__ == "__main__":
    unittest.main()
