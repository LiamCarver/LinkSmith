# Principles Jobs Canvas Effort Advisory Markdown

This pipeline combines:

- one principles Markdown folder
- one job specs Markdown folder
- one combined client-and-team canvas

and turns them into:

- one structured effort-distribution advisory JSON output
- one rendered Markdown advisory report

## Artifact Set

Files in this folder:

- `pipeline.json`
  Declares the workflow graph, external inputs, final outputs, and invocation-scoped resources.

- `registry.json`
  Declares the service contracts used by this pipeline.

- `runtime.json`
  Declares Docker image tags, argument wiring, and LM Studio environment settings used by the engine runner.

- `resources/effort-advisory.prompt.mustache`
  Fixed prompt resource bound to the LLM invocation.

- `resources/effort-advisory.schema.json`
  Fixed JSON Schema resource bound to the LLM invocation and also referenced by the local registry output contract.

- `resources/effort-advisory-report.template.mustache`
  Fixed Mustache template resource bound to the Markdown renderer invocation.

## External Run-Time Inputs

This pipeline expects three external run-time inputs:

- `principles_docs`
  - type: `markdown-directory`
  - mode: `directory`
  - cardinality: `one`

- `job_specs_docs`
  - type: `markdown-directory`
  - mode: `directory`
  - cardinality: `one`

- `context_canvas`
  - type: `obsidian-canvas`
  - mode: `file`
  - cardinality: `one`

## Invocation Resources

These are not supplied at run time:

- `resources/effort-advisory.prompt.mustache`
- `resources/effort-advisory.schema.json`
- `resources/effort-advisory-report.template.mustache`

They are fixed invocation-scoped resources resolved relative to `pipeline.json`.

## Final Outputs

- `advice`
  - structured JSON advice about how the team's effort should be distributed

- `document`
  - rendered Markdown advisory report

## Runtime Notes

Before running:

1. Build or retag the service images expected by `runtime.json`:
   - `linksmith-markdown-directory-to-json-corpus:engine-test`
   - `linksmith-obsidian-canvas-to-relationships:engine-test`
   - `linksmith-json-files-to-json-bundle:engine-test`
   - `linksmith-json-to-json-llm-transformer:engine-live-test`
   - `linksmith-json-to-markdown-renderer:engine-live-test`
2. Update `runtime.json` so `LINKSMITH_LLM_MODEL` matches a model actually loaded in LM Studio if needed.
3. Start LM Studio and ensure the OpenAI-compatible endpoint is reachable from Docker at `http://host.docker.internal:1234/v1`, or update `runtime.json` if your setup differs.

## Current Run Shape

Run from the repo root with `PYTHONPATH=src` configured.

Example:

```python
from pathlib import Path

from linksmith_engine.engine import PipelineRunRequest, run_pipeline
from linksmith_engine.runtime_loader import load_runtime_config, load_service_runner

pipeline_root = Path("pipelines/principles-jobs-canvas-effort-advisory-markdown")
runtime_config = load_runtime_config(pipeline_root / "runtime.json", validate_schema=False)
runner = load_service_runner(runtime_config)

result = run_pipeline(
    PipelineRunRequest(
        pipeline_path=pipeline_root / "pipeline.json",
        registry_path=pipeline_root / "registry.json",
        pipeline_inputs={
            "principles_docs": pipeline_root / "examples" / "input" / "principles",
            "job_specs_docs": pipeline_root / "examples" / "input" / "job-specs",
            "context_canvas": pipeline_root / "examples" / "input" / "context.canvas",
        },
        run_root=Path("runs"),
        run_id="effort-advisory-demo-001",
        validate_schema=False,
        validate_outputs=True,
        service_runner=runner,
    )
)

print(result.outputs["advice"][0])
print(result.outputs["document"][0])
```

## Data Flow

1. `markdown-directory-to-json-corpus` normalizes the principles folder.
2. `markdown-directory-to-json-corpus` normalizes the job specs folder.
3. `obsidian-canvas-to-relationships` normalizes the combined client-and-team canvas.
4. `json-files-to-json-bundle` combines all three normalized JSON artifacts into one provenance-preserving bundle.
5. `json-to-json-llm-transformer` generates the effort-distribution advisory JSON using the bound prompt and schema resources.
6. `json-to-markdown-renderer` renders the advisory JSON into Markdown using the bound Mustache template.

## Design Doc

The reviewed design note for this pipeline is here:

- [principles-jobs-canvas-effort-advisory-pipeline.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/components/pipelines/principles-jobs-canvas-effort-advisory-pipeline.md)
