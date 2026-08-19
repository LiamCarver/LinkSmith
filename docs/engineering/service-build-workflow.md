# Service Build Workflow

## Purpose

This workflow standardizes how new LinkSmith services should be built after the design doc has been reviewed.

The goal is to keep service implementation:

- contract-first
- deterministic-first where possible
- container-first in delivery shape
- backed by high-fidelity tests that exercise realistic artifacts on disk

## Scope

Use this workflow for new LinkSmith services, especially when they are expected to run as containerized pipeline steps later.

This workflow does not replace the mandatory design-first step. It starts after the service design has been reviewed and accepted.

## Required Sequence

1. Confirm the service design doc exists and has been reviewed.
2. Create realistic input and expected-output fixtures under `fixtures/services/<service-id>/`.
3. Promote any reusable expected artifacts into schema-level fixtures under `fixtures/artifacts/` when relevant.
4. Add a high-fidelity red test that checks the real service contract.
5. Scaffold the container interface and service entrypoint.
6. Run the red test and confirm the failure is meaningful.
7. Implement the deterministic or LLM-backed service logic.
8. Re-run local and container tests until green.
9. Note what `linksmith-core` helped with and what friction appeared.

## High-Fidelity TDD

The default expectation is that each new service gets at least one high-fidelity test before implementation.

That test should usually:

- use realistic fixtures from `fixtures/services/<service-id>/`
- invoke the service in the way it is expected to run for users or the engine
- compare actual emitted artifacts to expected artifacts on disk

Prefer canonical structure comparison for JSON outputs:

- parse JSON
- compare normalized structures
- avoid brittle raw-string comparisons unless formatting itself is the contract

## Container-First

The default delivery shape for LinkSmith services is container-first.

This means the service should usually have:

- a clear CLI or entrypoint
- a Dockerfile
- explicit mounted input and output paths

The purpose is not Docker for its own sake. The purpose is to keep service boundaries explicit and close to how the future engine will invoke services.

## Test Layers

Each service should usually have two layers of tests:

1. High-fidelity contract test
   - validates realistic file-in/file-out behavior
   - preferably includes container execution
2. Narrow deterministic unit tests
   - validate the core logic that is easiest to break
   - especially important for parsing, grouping, graph, or rendering logic

## Fixtures

Fixture expectations:

- realistic enough to exercise real logic
- small enough to review comfortably
- named clearly
- stored in stable repo paths

Suggested layout:

```text
fixtures/services/<service-id>/
  input/
  expected/
```

## Core Reflection

After a first implementation pass, record a short judgment about `linksmith-core`.

At minimum, answer:

1. What boilerplate did core remove?
2. What contract or runtime behavior was easy because of core?
3. What felt awkward, too local-Python-specific, or missing?

This reflection should feed future core and engine design rather than remaining implicit.

## Relationship To Future Conformance Checks

This workflow should remain deterministic enough that a future validator can check whether a service appears to conform.

Examples of future conformance checks:

- design doc exists
- fixtures exist
- Dockerfile exists
- high-fidelity test exists
- expected container interface is present

Those checks should be added later as deterministic tooling, not as a replacement for this workflow document.
