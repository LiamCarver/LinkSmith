# Obsidian Canvas Issues Markdown

This pipeline turns one Obsidian `.canvas` file into:

- deterministic `canvas-relationships` JSON
- schema-constrained issues JSON from the LLM transformer
- deterministic Markdown rendered from the issues JSON

## Artifact Set

Files in this folder:

- `pipeline.json`
  Declares the workflow graph, external input, final outputs, and invocation-scoped resources.

- `registry.json`
  Declares the service contracts used by this pipeline.

- `runtime.json`
  Declares Docker image tags, argument wiring, and LM Studio environment settings used by the engine runner.

- `resources/issues.prompt.mustache`
  Fixed prompt resource bound to the LLM invocation.

- `resources/issues.schema.json`
  Fixed JSON Schema resource bound to the LLM invocation and also referenced by the local registry output contract.

- `resources/issues-report.template.mustache`
  Fixed Mustache template resource bound to the Markdown renderer invocation.

## Local Registry Note

This pipeline keeps the generic `json-to-json-llm-transformer` contract stable by using a pipeline-local service id:

- `canvas-relationships-to-issues-json`

That local id points at the same shared transformer runtime image, but declares the narrower `canvas-relationships` input contract required by this workflow.

## External Run-Time Input

This pipeline expects one external run-time input:

- `canvas`
  - type: `obsidian-canvas`
  - mode: `file`
  - cardinality: `one`

## Invocation Resources

These are not supplied at run time:

- `resources/issues.prompt.mustache`
- `resources/issues.schema.json`
- `resources/issues-report.template.mustache`

They are fixed invocation-scoped resources resolved relative to `pipeline.json`.

## Final Outputs

- `issues`
  - structured JSON issue list from the LLM step

- `document`
  - rendered Markdown report from the renderer step

## Runtime Notes

Before running:

1. Build or retag the service images expected by `runtime.json`:
   - `linksmith-obsidian-canvas-to-relationships:engine-test`
   - `linksmith-json-to-json-llm-transformer:engine-live-test`
   - `linksmith-json-to-markdown-renderer:engine-live-test`
2. Update `runtime.json` so `LINKSMITH_LLM_MODEL` matches a model that is actually loaded in LM Studio.
3. Start LM Studio and ensure the OpenAI-compatible endpoint is reachable from Docker at `http://host.docker.internal:1234/v1`, or update `runtime.json` if your setup differs.

## Current Run Shape

Run from the repo root with `PYTHONPATH=src` configured.

Example:

```python
from pathlib import Path

from linksmith_engine.engine import PipelineRunRequest, run_pipeline
from linksmith_engine.runtime_loader import load_runtime_config, load_service_runner

pipeline_root = Path("pipelines/obsidian-canvas-issues-markdown")
runtime_config = load_runtime_config(pipeline_root / "runtime.json", validate_schema=False)
runner = load_service_runner(runtime_config)

result = run_pipeline(
    PipelineRunRequest(
        pipeline_path=pipeline_root / "pipeline.json",
        registry_path=pipeline_root / "registry.json",
        pipeline_inputs={
            "canvas": Path("C:/path/to/your/input.canvas"),
        },
        run_root=Path("runs"),
        run_id="canvas-issues-001",
        validate_schema=False,
        validate_outputs=True,
        service_runner=runner,
    )
)

print(result.outputs["issues"][0])
print(result.outputs["document"][0])
```

Run that from the repo root with `PYTHONPATH=src`.

## Data Flow

1. `obsidian-canvas-to-relationships` normalizes the external canvas input into relationships JSON.
2. `json-to-json-llm-transformer` extracts issue-oriented JSON using the bound prompt and bound schema resources.
3. `json-to-markdown-renderer` renders the issues JSON into Markdown using the bound Mustache template.

## Design Doc

The reviewed design note for this pipeline is here:

- [obsidian-canvas-issues-markdown-pipeline.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/components/pipelines/obsidian-canvas-issues-markdown-pipeline.md)
