# Obsidian Canvas Summary Markdown

This is a real LinkSmith pipeline that turns one Obsidian `.canvas` file into:

- deterministic `canvas-relationships` JSON
- schema-constrained summary JSON from the LLM transformer
- deterministic Markdown rendered from the summary JSON

## Artifact Set

Files in this folder:

- `pipeline.json`
  Declares the workflow graph, external input, final outputs, and invocation-scoped resources.

- `registry.json`
  Declares the service contracts used by this pipeline. This is local to the pipeline because the repo does not yet have one canonical shared runnable registry.

- `runtime.json`
  Declares Docker image tags, argument wiring, and LM Studio environment settings used by the engine runner.

- `resources/summary.prompt.mustache`
  Fixed prompt resource bound to the LLM invocation.

- `resources/summary.schema.json`
  Fixed JSON Schema resource bound to the LLM invocation and also referenced by the local registry output contract.

- `resources/summary-report.template.mustache`
  Fixed Mustache template resource bound to the Markdown renderer invocation.

## Local Registry Note

This pipeline keeps the generic `json-to-json-llm-transformer` contract stable by using a pipeline-local service id:

- `canvas-relationships-to-summary-json`

That local id points at the same shared transformer runtime image, but declares the narrower `canvas-relationships` input contract required by this specific workflow.

## External Run-Time Input

This pipeline expects one external run-time input:

- `canvas`
  - type: `obsidian-canvas`
  - mode: `file`
  - cardinality: `one`

## Invocation Resources

These are not supplied at run time:

- `resources/summary.prompt.mustache`
- `resources/summary.schema.json`
- `resources/summary-report.template.mustache`

They are fixed invocation-scoped resources resolved relative to `pipeline.json`.

## Final Outputs

- `summary`
  - structured JSON summary from the LLM step

- `document`
  - rendered Markdown report from the renderer step

## Runtime Notes

Before running:

1. Build or retag the service images expected by `runtime.json`:
   - `linksmith-obsidian-canvas-to-relationships:local`
   - `linksmith-json-to-json-llm-transformer:local`
   - `linksmith-json-to-markdown-renderer:local`
2. Update `runtime.json` so `LINKSMITH_LLM_MODEL` matches a model that is actually loaded in LM Studio.
3. Start LM Studio and ensure the OpenAI-compatible endpoint is reachable from Docker at `http://host.docker.internal:1234/v1`, or update `runtime.json` if your setup differs.

## Current Run Shape

There is not yet a dedicated repo CLI for running arbitrary pipelines.

Until that exists, run the pipeline from Python using the engine APIs. Example:

```python
from pathlib import Path

from linksmith_engine.engine import PipelineRunRequest, run_pipeline
from linksmith_engine.runtime_loader import load_runtime_config, load_service_runner

pipeline_root = Path("pipelines/obsidian-canvas-summary-markdown")
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
        run_id="canvas-summary-001",
        validate_schema=False,
        validate_outputs=True,
        service_runner=runner,
    )
)

print(result.outputs["summary"][0])
print(result.outputs["document"][0])
```

Run that from the repo root with `PYTHONPATH=src` configured.

PowerShell example:

```powershell
$env:PYTHONPATH="src"
python
```

Then paste the Python snippet above.

## Data Flow

1. `obsidian-canvas-to-relationships` normalizes the external canvas input into relationships JSON.
2. `json-to-json-llm-transformer` summarizes that JSON using the bound prompt and bound schema resources.
3. `json-to-markdown-renderer` renders the summary JSON into Markdown using the bound Mustache template.

## Design Doc

The reviewed design note for this pipeline is here:

- [docs/components/pipelines/obsidian-canvas-summary-markdown-pipeline.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/components/pipelines/obsidian-canvas-summary-markdown-pipeline.md)
