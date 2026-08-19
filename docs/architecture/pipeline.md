# Pipeline Spec Notes

## Purpose

A pipeline describes how registered services are wired together to transform artifacts.

The pipeline contract should answer:

- which services are used
- which concrete step and invocation instances exist
- what configuration each invocation receives
- how artifacts flow between invocations
- which external files enter and leave the pipeline

## Why A Graph Shape

The pipeline is easier to read if execution units and their connections are declared separately.

That suggests a graph-oriented model:

- `steps` declares the major stages
- each step contains one or more `invocations`
- `edges` declares the connections

This is clearer than embedding upstream/downstream wiring inside each step.

## v1 Design

The initial pipeline model is intentionally explicit:

- top-level pipeline metadata
- pipeline-level `inputs`
- pipeline-level `outputs`
- a `steps` array
- an `edges` array

Each step declares:

- `id`
- optional `description`
- an `invocations` array

Each invocation declares:

- `id`
- `service`
- optional `config`
- optional `description`
- optional `inputs`
- optional `outputs`

Each edge declares:

- `from`
- `to`
- optional `label`

## Pipeline Inputs And Outputs

The pipeline itself should also declare entry and exit points so it can be run as a reusable unit.

That means:

- `inputs`: named external artifacts expected by the pipeline
- `outputs`: named external artifacts produced by the pipeline

Edges can originate from pipeline inputs or terminate at pipeline outputs through reserved pseudo-endpoints:

- `pipeline:input.<port-name>`
- `pipeline:output.<port-name>`

Step outputs and inputs are addressed as fully-qualified artifact endpoints:

- `<step-id>.<invocation-id>.<port-name>`

This keeps the graph model consistent while avoiding name collisions.

## Validation Intent

The pipeline schema should validate structure, but not every semantic rule.

Structural rules:

- steps must have unique ids
- invocations must have ids
- edges must declare source and target endpoints
- pipeline inputs and outputs must be named and typed

Semantic rules to enforce later in the engine:

- every `service` must exist in the registry
- every referenced service port must exist on that service
- connected artifact types must be compatible
- connected modes and cardinalities must be compatible
- `pipeline:input.*` references must match declared pipeline inputs
- `pipeline:output.*` references must match declared pipeline outputs

## Open Questions

- Should step-level retry or cache policy live in pipeline config or service config?
- Should file paths live in the pipeline spec or in a separate run manifest?
- Should invocations be allowed to alias service ports for readability, or is the service port name enough in v1?
