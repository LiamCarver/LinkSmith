# Python Standards

## Purpose

These standards exist to keep LinkSmith predictable, reviewable, and safe as a contract-heavy Python project.

The project is built around:

- JSON Schema contracts
- deterministic JSON/Markdown transformations where possible
- explicit service lifecycles
- AI-assisted steps only where semantic synthesis is actually needed

## Typing

### Required

- Use type hints on all public functions, methods, and module-level constants where useful.
- Prefer explicit return types.
- Use `from __future__ import annotations`.

### Internal Models

- Prefer `dataclass` for structured in-memory models.
- Convert boundary JSON into typed Python models early.
- Keep raw `dict[str, Any]` and `list[Any]` at the boundary only.

### Avoid

- Passing nested untyped dictionaries deep through the codebase.
- Using `Any` unless there is a real boundary reason.
- Returning structurally ambiguous objects when a typed model is possible.

## JSON And Markdown Boundaries

### JSON

- Validate JSON inputs against schema as early as possible.
- Validate JSON outputs before writing them.
- Treat JSON Schema validation failures as first-class errors, not soft warnings.

### Markdown

- Prefer deterministic rendering from structured JSON.
- Avoid using LLMs for rendering when a template can do the job.

## Service Structure

Every registry-backed service should converge on the same lifecycle:

1. load inputs
2. validate inputs
3. transform or render
4. validate outputs
5. write outputs
6. emit useful logs and failure artifacts

Service implementations should keep orchestration separate from business logic.

## Deterministic First

The default architectural rule is:

- if deterministic code can do the transform exactly, use deterministic code
- use LLMs only for semantic interpretation, synthesis, extraction, or summarization

Examples of deterministic work:

- JSON -> JSON structural transforms
- JSON -> Markdown rendering
- file loading and writing
- graph construction
- schema validation
- type normalization

Examples of LLM-suitable work:

- issue extraction
- document distillation
- semantic consolidation
- context-aware synthesis

## Error Handling

- Raise explicit errors with concrete context.
- Distinguish:
  - transport/runtime failures
  - malformed JSON
  - schema validation failures
  - configuration errors
  - missing artifact errors

- Preserve failure artifacts when an LLM step fails:
  - raw response
  - validation errors
  - repaired output if attempted

## Logging

- Emit concise, stage-oriented logs.
- Logs should help a fresh reviewer understand:
  - what the service is doing
  - what it read
  - what it produced
  - where it failed

- Do not log excessive raw content by default.

## Testing

### Expected

- Unit tests for deterministic transforms
- Conformance tests for schemas and example fixtures
- Golden tests for JSON -> Markdown rendering where useful

### Strong Preference

- Test fixtures should be small and readable.
- Invalid fixture tests should fail for exactly one reason when possible.

## File And Module Conventions

- Prefer small focused modules.
- Keep service-specific logic close to the service.
- Keep shared validation/runtime utilities in the shared package once introduced.

## Review Expectations

A good LinkSmith change should be easy to answer these questions about:

1. What contract changed?
2. What schema or typed model enforces it?
3. Where is deterministic logic used instead of AI?
4. What tests or examples prove the behavior?
5. What failure mode is introduced or mitigated?
