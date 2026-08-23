# Pipeline Spec Notes

## Purpose

A pipeline describes how registered services are wired together to transform artifacts.

The pipeline contract should answer:

- which services are used
- which concrete step and invocation instances exist
- what configuration each invocation receives
- how artifacts flow between invocations
- which external files enter and leave the pipeline

The pipeline also needs to answer a question that became clearer once reusable renderers and LLM-backed services existed:

- which files are true run-time inputs
- which files are fixed invocation-scoped resources such as prompt templates, Markdown templates, and JSON Schemas

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
- optional `resources`
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

## Inputs Vs Resources

This is the main refinement to the earlier pipeline shape.

LinkSmith now needs to model two different categories of artifacts:

- `inputs`
  run-time artifacts supplied by the caller or by a parent workflow
- `resources`
  fixed invocation-scoped artifacts that configure how one service instance behaves

Examples of `resources`:

- LLM prompt templates
- LLM output JSON Schemas
- Markdown render templates
- few-shot example files
- static lookup JSON used only by one invocation

Examples of true pipeline `inputs`:

- client JSON extracted earlier in a workflow
- a folder of Markdown source files
- manual answers supplied by a user
- an Obsidian canvas file

The distinction matters because these are different concerns:

- pipeline inputs vary per run
- resources are usually stable files bound to one invocation definition

Without this split, reusable generic services appear more coupled to pipeline runs than they really are.

## Invocation Resources

Each invocation may declare a `resources` array.

Each resource declares:

- `name`
- `type`
- `mode`
- `cardinality`
- `path`
- optional `description`

These resources are mounted and loaded exactly like ordinary inputs at execution time, but their file paths come from the pipeline definition rather than the external run request.

Conceptually:

- pipeline inputs are resolved from the run request
- invocation resources are resolved from the pipeline definition
- both then become concrete service input artifacts

This keeps the service contract unchanged while making pipeline intent clearer.

Recommended rule:

- use `inputs` for data that should change per run
- use `resources` for fixed artifacts that exist to configure one invocation

## Validation Intent

The pipeline schema should validate structure, but not every semantic rule.

Structural rules:

- steps must have unique ids
- invocations must have ids
- edges must declare source and target endpoints
- pipeline inputs and outputs must be named and typed
- invocation resources must be named, typed, and have explicit paths

Semantic rules to enforce later in the engine:

- every `service` must exist in the registry
- every referenced service port must exist on that service
- connected artifact types must be compatible
- connected modes and cardinalities must be compatible
- `pipeline:input.*` references must match declared pipeline inputs
- `pipeline:output.*` references must match declared pipeline outputs
- resource names should match declared service input ports when they are used as bound inputs
- resource paths should exist and match declared mode expectations

## Binding Model

There are now three ways an invocation can receive what it needs:

1. from an upstream edge
2. from a pipeline input edge
3. from an invocation resource bound directly in the invocation definition

That means a generic service such as `json-to-json-llm-transformer` can be reused many times without code duplication:

- invocation A binds `prompt = risk-extraction.prompt.mustache`
- invocation A binds `schema = risk-list.schema.json`
- invocation B binds `prompt = question-generation.prompt.mustache`
- invocation B binds `schema = question-list.schema.json`

Same service implementation, different resources.

## Example Shape

```json
{
  "id": "risk-report-pipeline",
  "inputs": [
    {
      "name": "client-summary",
      "type": "json-document",
      "mode": "file",
      "cardinality": "one"
    }
  ],
  "outputs": [
    {
      "name": "risk-report",
      "type": "markdown-document",
      "mode": "file",
      "cardinality": "one"
    }
  ],
  "steps": [
    {
      "id": "extract_risks",
      "invocations": [
        {
          "id": "risks",
          "service": "json-to-json-llm-transformer",
          "resources": [
            {
              "name": "prompt",
              "type": "mustache-template",
              "mode": "file",
              "cardinality": "one",
              "path": "resources/prompts/risk-extraction.mustache"
            },
            {
              "name": "schema",
              "type": "json-document",
              "mode": "file",
              "cardinality": "one",
              "path": "resources/schemas/risk-list.schema.json"
            }
          ]
        }
      ]
    },
    {
      "id": "render_report",
      "invocations": [
        {
          "id": "report",
          "service": "json-to-markdown-renderer",
          "resources": [
            {
              "name": "template",
              "type": "mustache-template",
              "mode": "file",
              "cardinality": "one",
              "path": "resources/templates/risk-report.mustache"
            }
          ]
        }
      ]
    }
  ],
  "edges": [
    {
      "from": "pipeline:input.client-summary",
      "to": "extract_risks.risks.data"
    },
    {
      "from": "extract_risks.risks.result",
      "to": "render_report.report.data"
    },
    {
      "from": "render_report.report.document",
      "to": "pipeline:output.risk-report"
    }
  ]
}
```

## Open Questions

- Should step-level retry or cache policy live in pipeline config or service config?
- Should invocation resource paths always be relative to the pipeline file, or allow explicit absolute paths for local-only runs?
- Should invocations be allowed to alias service ports for readability, or is the service port name enough in v1?
