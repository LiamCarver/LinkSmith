# New Service Checklist

Use this before implementation starts.

## Design

- A service design doc exists under `docs/components/services/` or another clearly appropriate `docs/components/` path.
- The purpose of the service is clear.
- It is clear why this should be a separate service.
- Deterministic vs LLM rationale is explicit.
- Inputs and outputs are defined clearly.
- A Mermaid data-flow diagram exists for non-trivial services.

## Contracts

- Planned input ports are identified.
- Planned output ports are identified.
- Types, modes, and cardinality are stated.
- Schema refs are identified for JSON ports.
- Registry implications are noted.

## Failure Handling

- Likely failure modes are documented.
- Validation points are identified.
- For LLM-backed services, malformed JSON and retry behavior are acknowledged.

## Examples And Tests

- Expected example fixtures are identified.
- Expected service fixtures under `fixtures/services/<service-id>/` are identified.
- Expected schema updates are identified.
- Expected deterministic unit tests or golden tests are identified.
- Expected high-fidelity contract test is identified.
- Expected container execution path is identified.
- A plan exists for a meaningful red test before implementation.

## Review Readiness

- The design doc is ready for review before code begins.
- Open questions are visible instead of being hidden in implementation.

## Post-Implementation Reflection

- The implementation captures what `linksmith-core` helped with.
- The implementation captures any core friction that should inform future design.
