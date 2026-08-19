from __future__ import annotations

import importlib
import json
from pathlib import Path

from .errors import ConfigurationError, SchemaDependencyError, SchemaValidationError
from .models import JsonValue


class SchemaValidator:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir
        self._cache: dict[Path, dict[str, object]] = {}

    def validate(self, payload: JsonValue, schema_ref: str) -> None:
        jsonschema = self._load_jsonschema_module()
        schema = self._load_schema(schema_ref)
        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
        if errors:
            messages = [error.message for error in errors]
            raise SchemaValidationError(schema_ref=schema_ref, errors=messages)

    def _load_jsonschema_module(self):  # type: ignore[no-untyped-def]
        module = importlib.util.find_spec("jsonschema")
        if module is None:
            raise SchemaDependencyError(
                "JSON Schema validation requires the 'jsonschema' package to be installed."
            )
        return importlib.import_module("jsonschema")

    def _load_schema(self, schema_ref: str) -> dict[str, object]:
        path = self._resolve_schema_path(schema_ref)
        cached = self._cache.get(path)
        if cached is not None:
            return cached
        with path.open("r", encoding="utf-8") as handle:
            schema = json.load(handle)
        if not isinstance(schema, dict):
            raise ConfigurationError(f"Schema file must contain a JSON object: {path}")
        self._cache[path] = schema
        return schema

    def _resolve_schema_path(self, schema_ref: str) -> Path:
        candidate = Path(schema_ref)
        if candidate.is_absolute():
            return candidate.resolve()
        if self._base_dir is None:
            raise ConfigurationError(
                f"Relative schemaRef '{schema_ref}' requires a schema_base_dir."
            )
        return (self._base_dir / candidate).resolve()
