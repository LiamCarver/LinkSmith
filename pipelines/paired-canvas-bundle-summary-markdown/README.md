# Paired Canvas Bundle Summary Markdown

This pipeline turns two Obsidian `.canvas` files into:

- deterministic `canvas-relationships` JSON for each source canvas
- one deterministic provenance-preserving `json-bundle` artifact
- one schema-constrained combined summary JSON from the LLM transformer
- one deterministic Markdown report rendered from that summary

## Artifact Set

Files in this folder:

- `pipeline.json`
  Declares the workflow graph, external inputs, final outputs, and invocation-scoped resources.

- `registry.json`
  Declares the service contracts used by this pipeline.

- `runtime.json`
  Declares Docker image tags, argument wiring, and LM Studio environment settings used by the engine runner.

- `resources/combined-summary.prompt.mustache`
  Fixed prompt resource bound to the LLM invocation.

- `resources/combined-summary.schema.json`
  Fixed JSON Schema resource bound to the LLM invocation and also referenced by the local registry output contract.

- `resources/combined-summary-report.template.mustache`
  Fixed Mustache template resource bound to the Markdown renderer invocation.

## External Run-Time Inputs

This pipeline expects two external run-time inputs:

- `team_canvas`
  - type: `obsidian-canvas`
  - mode: `file`
  - cardinality: `one`

- `client_canvas`
  - type: `obsidian-canvas`
  - mode: `file`
  - cardinality: `one`

## Invocation Resources

These are not supplied at run time:

- `resources/combined-summary.prompt.mustache`
- `resources/combined-summary.schema.json`
- `resources/combined-summary-report.template.mustache`

They are fixed invocation-scoped resources resolved relative to `pipeline.json`.

## Final Outputs

- `summary`
  - structured JSON summary across both canvases

- `document`
  - rendered Markdown report from that summary

## Runtime Notes

Before running:

1. Build or retag the service images expected by `runtime.json`:
   - `linksmith-obsidian-canvas-to-relationships:engine-test`
   - `linksmith-json-files-to-json-bundle:engine-test`
   - `linksmith-json-to-json-llm-transformer:engine-live-test`
   - `linksmith-json-to-markdown-renderer:engine-live-test`
2. Update `runtime.json` so `LINKSMITH_LLM_MODEL` matches a model that is actually loaded in LM Studio if needed.
3. Start LM Studio and ensure the OpenAI-compatible endpoint is reachable from Docker at `http://host.docker.internal:1234/v1`, or update `runtime.json` if your setup differs.

## Current Run Shape

Run from the repo root with `PYTHONPATH=src` configured.

Example:

```python
from pathlib import Path

from linksmith_engine.engine import PipelineRunRequest, run_pipeline
from linksmith_engine.runtime_loader import load_runtime_config, load_service_runner

pipeline_root = Path("pipelines/paired-canvas-bundle-summary-markdown")
runtime_config = load_runtime_config(pipeline_root / "runtime.json", validate_schema=False)
runner = load_service_runner(runtime_config)

result = run_pipeline(
    PipelineRunRequest(
        pipeline_path=pipeline_root / "pipeline.json",
        registry_path=pipeline_root / "registry.json",
        pipeline_inputs={
            "team_canvas": pipeline_root / "examples" / "input" / "sample-team.canvas",
            "client_canvas": pipeline_root / "examples" / "input" / "sample-client.canvas",
        },
        run_root=Path("runs"),
        run_id="paired-canvas-demo-001",
        validate_schema=False,
        validate_outputs=True,
        service_runner=runner,
    )
)

print(result.outputs["summary"][0])
print(result.outputs["document"][0])
```

## Data Flow

1. `obsidian-canvas-to-relationships` normalizes the team canvas.
2. `obsidian-canvas-to-relationships` normalizes the client canvas.
3. `canvas-relationships-to-json-bundle` combines both JSON artifacts into one provenance-preserving bundle.
4. `json-to-json-llm-transformer` summarizes the bundle using the bound prompt and bound schema resources.
5. `json-to-markdown-renderer` renders the summary JSON into Markdown using the bound Mustache template.

## Design Doc

The reviewed design note for this pipeline is here:

- [paired-canvas-bundle-summary-markdown-pipeline.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/components/pipelines/paired-canvas-bundle-summary-markdown-pipeline.md)
