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
