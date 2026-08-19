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
- Python standards and PR review guidance

## Review And Quality

See:

- [docs/python-standards.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/python-standards.md)
- [docs/pr-review.md](C:/Users/Liam/Documents/GitHub/LinkSmith/docs/pr-review.md)

For branch comparison and AI-friendly review input, use:

- [scripts/review-branch.ps1](C:/Users/Liam/Documents/GitHub/LinkSmith/scripts/review-branch.ps1)
