from __future__ import annotations

import json
from pathlib import Path

from .models import InvocationManifest, RunManifest


def write_invocation_manifest(path: Path, manifest: InvocationManifest) -> None:
    _write_json(
        path,
        {
            "stepId": manifest.step_id,
            "invocationId": manifest.invocation_id,
            "service": manifest.service_id,
            "status": manifest.status,
            "inputs": {key: list(value) for key, value in manifest.inputs.items()},
            "outputs": {key: list(value) for key, value in manifest.outputs.items()},
            "exitCode": manifest.exit_code,
            "logPath": manifest.log_path,
            "error": manifest.error,
        },
    )


def write_run_manifest(path: Path, manifest: RunManifest) -> None:
    _write_json(
        path,
        {
            "pipelineId": manifest.pipeline_id,
            "runId": manifest.run_id,
            "status": manifest.status,
            "invocationManifests": list(manifest.invocation_manifests),
            "outputs": {key: list(value) for key, value in manifest.outputs.items()},
            "error": manifest.error,
        },
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
