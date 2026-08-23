from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any, Protocol

import chevron

from linksmith_core.errors import ConfigurationError, SchemaDependencyError
from linksmith_core.models import JsonArtifact, JsonOutput, MarkdownArtifact, PortContract, ServiceContract, ServiceRunRequest
from linksmith_core.runtime import run_service


class ChatCompletionClient(Protocol):
    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> str:
        ...


@dataclass(frozen=True)
class OpenAiCompatibleClient:
    base_url: str
    api_key: str
    timeout_seconds: int

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> str:
        endpoint = _chat_completions_endpoint(self.base_url)
        request_payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed with HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc

        payload = json.loads(raw)
        try:
            choice = payload["choices"][0]
            message = choice["message"]
            content = message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("LLM response did not contain choices[0].message.content.") from exc
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            if parts:
                return "".join(parts)
        raise RuntimeError("LLM response content was not a supported text shape.")


def render_prompt(payload: dict[str, Any], template: str, output_schema: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        raise ConfigurationError("Transformer data JSON root must be an object.")
    if not isinstance(output_schema, dict):
        raise ConfigurationError("Transformer schema JSON root must be an object.")
    rendered = chevron.render(
        template,
        {
            "input": payload,
            "input_json": json.dumps(payload, indent=2, ensure_ascii=False),
            "output_schema": output_schema,
            "output_schema_json": json.dumps(output_schema, indent=2, ensure_ascii=False),
        },
    )
    if not rendered.strip():
        raise ConfigurationError("Rendered prompt must not be empty.")
    return rendered


def transform_json_document(
    payload: dict[str, Any],
    prompt_template: str,
    output_schema: dict[str, Any],
    *,
    client: ChatCompletionClient,
    model: str,
    temperature: float,
    max_retries: int,
) -> dict[str, Any]:
    prompt = render_prompt(payload, prompt_template, output_schema)
    previous_response: str | None = None
    previous_error: str | None = None
    attempts = max_retries + 1
    for attempt_index in range(attempts):
        messages = _build_messages(prompt, previous_response=previous_response, previous_error=previous_error)
        response_text = client.complete(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        try:
            candidate = extract_json_object(response_text)
            validate_output_schema(candidate, output_schema)
            return candidate
        except (ConfigurationError, RuntimeError) as exc:
            previous_response = response_text
            previous_error = str(exc)
            if attempt_index == attempts - 1:
                raise RuntimeError(
                    f"LLM response did not satisfy the expected JSON contract after {attempts} attempts: {exc}"
                ) from exc
    raise RuntimeError("LLM transformation exhausted retries without returning a result.")


class JsonToJsonLlmTransformerService:
    contract = ServiceContract(
        service_id="json-to-json-llm-transformer",
        inputs=(
            PortContract(
                name="data",
                type="json-document",
                mode="file",
                cardinality="one",
            ),
            PortContract(
                name="prompt",
                type="mustache-template",
                mode="file",
                cardinality="one",
            ),
            PortContract(
                name="schema",
                type="json-document",
                mode="file",
                cardinality="one",
            ),
        ),
        outputs=(
            PortContract(
                name="result",
                type="json-document",
                mode="file",
                cardinality="one",
            ),
        ),
        version="0.1.0",
    )

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.0,
        max_retries: int = 2,
        timeout_seconds: int = 60,
        output_file_name: str = "result.json",
        client: ChatCompletionClient | None = None,
    ) -> None:
        if not model.strip():
            raise ConfigurationError("LLM model must be configured.")
        if not base_url.strip():
            raise ConfigurationError("LLM base URL must be configured.")
        if max_retries < 0:
            raise ConfigurationError("LLM max retries must be zero or greater.")
        if timeout_seconds <= 0:
            raise ConfigurationError("LLM timeout must be greater than zero.")
        self._model = model
        self._temperature = temperature
        self._max_retries = max_retries
        self._output_file_name = output_file_name
        self._client = client or OpenAiCompatibleClient(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    def execute(self, inputs, context):
        data_artifact = inputs["data"][0]
        prompt_artifact = inputs["prompt"][0]
        schema_artifact = inputs["schema"][0]
        if not isinstance(data_artifact, JsonArtifact):
            raise ConfigurationError("Transformer data input must be loaded as a JSON artifact.")
        if not isinstance(prompt_artifact, MarkdownArtifact):
            raise ConfigurationError("Transformer prompt input must be loaded as a text artifact.")
        if not isinstance(schema_artifact, JsonArtifact):
            raise ConfigurationError("Transformer schema input must be loaded as a JSON artifact.")
        if not isinstance(data_artifact.data, dict):
            raise ConfigurationError("Transformer data JSON root must be an object.")
        if not isinstance(schema_artifact.data, dict):
            raise ConfigurationError("Transformer schema JSON root must be an object.")

        result = transform_json_document(
            data_artifact.data,
            prompt_artifact.text,
            schema_artifact.data,
            client=self._client,
            model=self._model,
            temperature=self._temperature,
            max_retries=self._max_retries,
        )
        context.metadata["model"] = self._model
        return {
            "result": JsonOutput(
                relative_path=PurePath(self._output_file_name),
                data=result,
            )
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transform JSON into JSON using an OpenAI-compatible chat-completions API."
    )
    parser.add_argument("--data", required=True, help="Path to the JSON data input file.")
    parser.add_argument("--prompt", required=True, help="Path to the prompt Mustache template file.")
    parser.add_argument("--schema", required=True, help="Path to the expected output JSON schema file.")
    parser.add_argument("--base-url", default=os.environ.get("LINKSMITH_LLM_BASE_URL"), help="OpenAI-compatible base URL, for example http://host.docker.internal:1234/v1.")
    parser.add_argument("--api-key", default=os.environ.get("LINKSMITH_LLM_API_KEY", "lm-studio"), help="API key for the OpenAI-compatible endpoint.")
    parser.add_argument("--model", default=os.environ.get("LINKSMITH_LLM_MODEL"), help="Model name to send to the API.")
    parser.add_argument("--temperature", type=float, default=float(os.environ.get("LINKSMITH_LLM_TEMPERATURE", "0")), help="Sampling temperature for the request.")
    parser.add_argument("--max-retries", type=int, default=int(os.environ.get("LINKSMITH_LLM_MAX_RETRIES", "2")), help="Number of retries after invalid JSON or schema-mismatched output.")
    parser.add_argument("--timeout-seconds", type=int, default=int(os.environ.get("LINKSMITH_LLM_TIMEOUT_SECONDS", "60")), help="HTTP timeout for the LLM request.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the result output port folder should be written.",
    )
    parser.add_argument(
        "--output-file-name",
        default="result.json",
        help="Output JSON filename relative to the result port directory.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    service = JsonToJsonLlmTransformerService(
        model=args.model or "",
        base_url=args.base_url or "",
        api_key=args.api_key,
        temperature=args.temperature,
        max_retries=args.max_retries,
        timeout_seconds=args.timeout_seconds,
        output_file_name=args.output_file_name,
    )
    request = ServiceRunRequest(
        inputs={
            "data": Path(args.data),
            "prompt": Path(args.prompt),
            "schema": Path(args.schema),
        },
        output_root=Path(args.output_dir),
    )
    result = run_service(service, request)
    for port_name, paths in result.written_outputs.items():
        for path in paths:
            print(f"{port_name}: {path}")
    return 0


def extract_json_object(text: str) -> dict[str, Any]:
    candidate = _try_parse_json(text)
    if isinstance(candidate, dict):
        return candidate
    if candidate is not None:
        raise ConfigurationError("LLM response JSON root must be an object.")

    fenced = _strip_code_fence(text)
    candidate = _try_parse_json(fenced)
    if isinstance(candidate, dict):
        return candidate
    if candidate is not None:
        raise ConfigurationError("LLM response JSON root must be an object.")

    for snippet in _iter_json_snippets(text):
        candidate = _try_parse_json(snippet)
        if isinstance(candidate, dict):
            return candidate
        if candidate is not None:
            raise ConfigurationError("LLM response JSON root must be an object.")
    raise ConfigurationError("LLM response did not contain a valid JSON object.")


def validate_output_schema(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    jsonschema = _load_jsonschema_module()
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        messages = [error.message for error in errors]
        raise ConfigurationError(f"LLM response did not satisfy output schema: {'; '.join(messages)}")


def _build_messages(
    prompt: str,
    *,
    previous_response: str | None,
    previous_error: str | None,
) -> list[dict[str, str]]:
    messages = [
        {
            "role": "system",
            "content": "You are a JSON transformation service. Return only one JSON object and no extra prose.",
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]
    if previous_response is not None and previous_error is not None:
        messages.extend(
            [
                {"role": "assistant", "content": previous_response},
                {
                    "role": "user",
                    "content": (
                        "Your previous response was invalid. "
                        f"Problem: {previous_error}. Return only one valid JSON object that satisfies the schema."
                    ),
                },
            ]
        )
    return messages


def _chat_completions_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _try_parse_json(text: str) -> Any | None:
    candidate = text.strip()
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```") or not stripped.endswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 3:
        return stripped
    return "\n".join(lines[1:-1]).strip()


def _iter_json_snippets(text: str):
    starts = [index for index, char in enumerate(text) if char in "{["]
    for start in starts:
        snippet = _balanced_json_snippet(text, start)
        if snippet is not None:
            yield snippet


def _balanced_json_snippet(text: str, start: int) -> str | None:
    opening = text[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == "\"":
                in_string = False
            continue
        if char == "\"":
            in_string = True
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _load_jsonschema_module():
    module = importlib.util.find_spec("jsonschema")
    if module is None:
        raise SchemaDependencyError(
            "JSON Schema validation requires the 'jsonschema' package to be installed."
        )
    return importlib.import_module("jsonschema")


if __name__ == "__main__":
    raise SystemExit(main())
