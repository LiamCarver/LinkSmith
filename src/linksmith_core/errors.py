from __future__ import annotations

from pathlib import Path


class LinksmithError(Exception):
    """Base class for LinkSmith runtime failures."""


class ConfigurationError(LinksmithError):
    """Raised when a service contract or runtime config is invalid."""


class ArtifactError(LinksmithError):
    """Raised for artifact loading or interpretation failures."""


class MissingArtifactError(ArtifactError):
    """Raised when an expected file or directory does not exist."""

    def __init__(self, path: Path, message: str | None = None) -> None:
        detail = message or f"Expected artifact does not exist: {path}"
        super().__init__(detail)
        self.path = path


class UnsupportedArtifactModeError(ArtifactError):
    """Raised when a port mode or artifact type is not supported."""


class MalformedJsonError(ArtifactError):
    """Raised when a JSON artifact cannot be parsed."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"Malformed JSON in {path}: {message}")
        self.path = path


class SchemaDependencyError(ConfigurationError):
    """Raised when JSON Schema validation is requested without the dependency."""


class SchemaValidationError(LinksmithError):
    """Raised when JSON data fails schema validation."""

    def __init__(self, schema_ref: str, errors: list[str]) -> None:
        super().__init__(f"Schema validation failed for {schema_ref}")
        self.schema_ref = schema_ref
        self.errors = tuple(errors)


class ServiceExecutionError(LinksmithError):
    """Raised when service logic fails unexpectedly."""


class OutputWriteError(LinksmithError):
    """Raised when an output artifact cannot be written."""
