from __future__ import annotations


class EngineError(Exception):
    """Base class for engine-level failures."""


class PipelineValidationError(EngineError):
    """Raised when the pipeline and registry are structurally or semantically incompatible."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("Pipeline validation failed")
        self.errors = tuple(errors)


class ServiceRunnerError(EngineError):
    """Raised when a service runner cannot execute an invocation successfully."""
