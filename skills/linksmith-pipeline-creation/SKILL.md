---
name: linksmith-pipeline-creation
description: "Create or update a real LinkSmith pipeline after clarifying the workflow in repo-local design documentation, with explicit pipeline artifacts, invocation resources, and runnable examples."
---

# Linksmith Pipeline Creation

Use this skill when the task is to create or update a real LinkSmith pipeline as a reusable workflow in this repository.

This skill does not replace the design-first workflow. For meaningful new pipeline work, the design documentation must exist or be updated and be reviewed before pipeline artifacts or pipeline-related code are written.

## Goal

Create or update a real pipeline in a way that keeps the workflow:

- design-first
- contract-first
- explicit about run-time inputs vs invocation resources
- runnable outside test-only fixtures

## Required Inputs

Before implementation, confirm that the pipeline work already has:

- a reviewed design doc or updated design doc that explains the workflow
- named external run-time inputs
- named final outputs
- identified services and artifact contracts

If those are missing, stop implementation work and follow the existing `linksmith-design-docs` workflow first.

## Required Workflow

For meaningful pipeline work, the default sequence is:

1. create or update the design doc first
2. stop for user review before implementation
3. create or update a real pipeline folder in the repo
4. add or update `pipeline.json`
5. add or update `runtime.json`
6. add or update `resources/` files used as invocation-scoped resources
7. add or update `README.md` for the pipeline
8. run validation and, when inputs are available, run the pipeline end to end

## Standard Pipeline Shape

Prefer a real pipeline folder such as:

```text
pipelines/<pipeline-id>/
  README.md
  pipeline.json
  runtime.json
  resources/
```

Add `registry.json` beside the pipeline only when the example cannot yet rely on a stable shared executable registry elsewhere in the repo.

## References

Read these before implementing or changing a pipeline:

- `README.md`
- `docs/architecture/pipeline.md`
- `docs/architecture/registry.md`
- `docs/components/engine/linksmith-engine.md`

Read only the service docs relevant to the services used by the target pipeline.

## Constraints

- Treat the design doc as a non-negotiable first step for meaningful pipeline work.
- Distinguish true external `inputs` from invocation-scoped `resources`.
- Prefer invocation `resources` for prompts, templates, schemas, and other fixed files bound to one invocation.
- Keep Docker image tags, argument wiring, and environment mappings in `runtime.json`, not `pipeline.json`.
- Prefer a real pipeline folder over embedding the example only in test fixture payloads.
- Keep the pipeline README aligned with the actual artifact set and run command.

## Review Standard

When updating a pipeline, review these together:

- the design doc
- `pipeline.json`
- `runtime.json`
- `registry.json` if present
- resource files under `resources/`
- the pipeline `README.md`

If one changes and the others become misleading, update them in the same change set.

## Notes

- This skill exists to standardize pipeline creation the same way `linksmith-service-build` standardizes service creation.
- Pair it with `linksmith-review` once the pipeline changes exist and need branch review.
