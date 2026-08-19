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
- example registry and pipeline fixtures
- an initial shared Python runtime package in `src/linksmith_core`
- Python standards and PR review guidance
- service documentation standards and templates

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

The first concrete deterministic service is planned as:

- `obsidian-canvas-to-relationships`

It is intended to be container-first and reusable both as a standalone tool and as a future pipeline step.

## Review And Quality

See:

- [docs/engineering/python-standards.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/engineering/python-standards.md)
- [docs/engineering/pr-review.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/engineering/pr-review.md)
- [docs/architecture/service-standards.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/architecture/service-standards.md)
- [docs/templates/service-design-template.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/templates/service-design-template.md)
- [docs/checklists/new-service-checklist.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/checklists/new-service-checklist.md)

For branch comparison and AI-friendly review input, use:

- [scripts/review-branch.ps1](C:/Users/Liam/Documents/GitHub/LinkSmith/scripts/review-branch.ps1)
