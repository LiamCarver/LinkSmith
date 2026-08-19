# Service Documentation Standards

## Purpose

These standards define the minimum documentation inputs required before implementing a new LinkSmith service.

The goal is to make service design reviewable before code exists.

## Non-Negotiable Rule

For any new LinkSmith service, create or update the service design documentation before implementation begins.

This applies whether the service is:

- deterministic
- LLM-backed
- a renderer
- a helper used by the pipeline engine

## Required Location

Each new service should have a design doc at:

```text
docs/components/services/<service-id>.md
```

If the change is not a standalone service, use a nearby `docs/components/` location that matches the component clearly.

## Required Sections

Every new service design doc should include:

1. Purpose
2. Why this should exist as a separate service
3. Deterministic vs LLM rationale
4. Inputs
5. Outputs
6. Registry contract implications
7. Data flow
8. Mermaid diagram
9. Failure modes
10. Example artifacts or schema refs
11. Open questions
12. Implementation notes

## Input And Output Expectations

The doc should state:

- input port names
- output port names
- artifact types
- modes
- cardinality
- relevant schema refs

This should line up with the eventual registry declaration.

## Deterministic vs LLM

The doc must explicitly justify whether the service is:

- deterministic
- LLM-backed

Default expectation:

- deterministic first when exact code can do the transform
- LLM only when semantic synthesis or fuzzy extraction is genuinely needed

## Data Flow

A Mermaid diagram should be included whenever the service is non-trivial.

At minimum, the diagram should show:

- service inputs
- validation points
- transform stage
- output validation
- emitted outputs

## Failure Modes

The doc should explicitly call out likely failure classes, for example:

- malformed input JSON
- schema validation failures
- missing files
- invalid configuration
- LLM malformed JSON
- retry exhaustion

## Relationship To Review

The design doc is the thing to review before implementation.

The code review comes later. The service design doc is the input contract for that implementation work.
