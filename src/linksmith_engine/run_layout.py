from __future__ import annotations

import shutil
from pathlib import Path

from .models import RunPaths


def create_run_layout(run_root: Path, run_id: str, pipeline_path: Path, registry_path: Path) -> RunPaths:
    root = run_root / run_id
    pipeline_dir = root / "pipeline"
    inputs_dir = root / "inputs"
    invocation_artifacts_dir = root / "invocation-artifacts"
    manifests_dir = root / "manifests"
    invocation_manifests_dir = manifests_dir / "invocations"
    logs_dir = root / "logs"
    invocation_logs_dir = logs_dir / "invocations"
    outputs_dir = root / "outputs"

    for directory in (
        pipeline_dir,
        inputs_dir,
        invocation_artifacts_dir,
        manifests_dir,
        invocation_manifests_dir,
        logs_dir,
        invocation_logs_dir,
        outputs_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    pipeline_file = pipeline_dir / "pipeline.json"
    registry_file = pipeline_dir / "registry.json"
    shutil.copy2(pipeline_path, pipeline_file)
    shutil.copy2(registry_path, registry_file)
    run_manifest_file = manifests_dir / "run.json"
    engine_log_file = logs_dir / "engine.log"

    return RunPaths(
        run_id=run_id,
        root=root,
        pipeline_dir=pipeline_dir,
        inputs_dir=inputs_dir,
        invocation_artifacts_dir=invocation_artifacts_dir,
        manifests_dir=manifests_dir,
        invocation_manifests_dir=invocation_manifests_dir,
        logs_dir=logs_dir,
        invocation_logs_dir=invocation_logs_dir,
        outputs_dir=outputs_dir,
        pipeline_file=pipeline_file,
        registry_file=registry_file,
        run_manifest_file=run_manifest_file,
        engine_log_file=engine_log_file,
    )
