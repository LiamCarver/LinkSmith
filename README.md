# LinkSmith

LinkSmith is a spec-driven workflow engine for chaining small services over Markdown and JSON artifacts.

The design goal is to make pipelines explicit, composable, and inspectable:

- services are declared in a registry
- services declare input and output contracts
- pipelines reference registered services
- deterministic services are preferred where exact code can replace fuzzy AI behavior

The repository currently starts with:

- a service registry contract
- a pipeline definition contract
- fixture-driven example registries, runtime configs, and pipelines
- an initial shared Python runtime package in `src/linksmith_core`
- an initial local-Python engine package in `src/linksmith_engine`
- three implemented services in `src/linksmith_services`
- Python standards and PR review guidance
- service documentation standards and templates

The current repository shape is still fixture-first.

- most runnable examples are defined in test fixtures rather than as standalone pipeline folders
- the engine runtime is real and exercised end to end in tests
- a canonical non-test pipeline folder is not in place yet

Read these docs first if you want the current code shape rather than the earlier design intent:

- [docs/components/engine/linksmith-engine.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/components/engine/linksmith-engine.md)
- [docs/architecture/pipeline.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/architecture/pipeline.md)
- [docs/architecture/registry.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/architecture/registry.md)

## Core Package

The first implementation layer is `linksmith_core`, a deterministic shared package for:

- JSON and Markdown artifact loading
- optional JSON Schema validation hooks
- a protocol-based service interface
- a standard service runner
- structured stage logs

Current constraints:

- JSON Schema validation depends on the `jsonschema` package declared in `pyproject.toml`
- directory inputs currently normalize recursive Markdown collections only
- LLM helpers and Markdown rendering helpers remain outside core by design

Run the current unit tests with:

```text
$env:PYTHONPATH="src"
python -m unittest discover -s tests
```

## Services

Implemented services:

- `obsidian-canvas-to-relationships`
- `json-to-markdown-renderer`
- `json-to-json-llm-transformer`

All current services are intended to be container-first and reusable both as standalone tools and as future pipeline steps.

## Engine

The current engine slice supports:

- local Python orchestration
- pipeline and registry loading
- semantic pipeline validation
- declarative runtime-config loading for Docker-backed services
- deterministic host run-folder creation
- service execution through a runner abstraction
- Docker-backed service execution for containerized services
- invocation-scoped resource binding
- output contract enforcement
- optional JSON Schema validation of emitted JSON artifacts
- per-invocation and per-run manifests

Current important distinction:

- `pipeline_inputs` are external artifacts supplied at run time
- invocation `resources` are fixed files declared inside the pipeline definition and resolved by the engine

Current highest-fidelity coverage is still test-driven:

- [tests/test_engine.py](C:/Users/Liam/Documents/GitHub/LinkSmith/tests/test_engine.py) covers invocation-scoped resources with fixture-driven engine runs
- [tests/test_engine_docker.py](C:/Users/Liam/Documents/GitHub/LinkSmith/tests/test_engine_docker.py) covers real Docker-backed runs, including a live LM Studio path
- the live Docker test still passes prompt, schema, and template as top-level pipeline inputs rather than invocation resources

## Review And Quality

See:

- [docs/engineering/python-standards.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/engineering/python-standards.md)
- [docs/engineering/pr-review.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/engineering/pr-review.md)
- [docs/architecture/service-standards.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/architecture/service-standards.md)
- [docs/templates/service-design-template.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/templates/service-design-template.md)
- [docs/checklists/new-service-checklist.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/checklists/new-service-checklist.md)

For branch comparison and AI-friendly review input, use:

- [scripts/review-branch.ps1](C:/Users/Liam/Documents/GitHub/LinkSmith/scripts/review-branch.ps1)
