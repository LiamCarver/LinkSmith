---
name: linksmith-design-docs
description: "For meaningful LinkSmith changes, create or update design documentation before implementation so the component model and data flow can be reviewed first."
---

# Linksmith Design Docs

For meaningful LinkSmith work, this is the default first step. Do not begin implementation of a new service, engine component, or meaningful architectural change until the design documentation has been created or updated.

## Goal

Produce or update a repo-local Markdown design note that explains:

- the purpose of the change
- the main code components that will exist
- the expected inputs and outputs
- the data flow between components
- constraints and open questions

Use Mermaid diagrams when they improve clarity.

## Expected Output

Create or update a Markdown doc, typically under `docs/components/` or another clearly named design-doc location in the repo.

For new services specifically, use:

- `docs/architecture/service-standards.md`
- `docs/templates/service-design-template.md`
- `docs/checklists/new-service-checklist.md`

A good design note should usually include:

- purpose
- scope
- main components
- inputs and outputs
- data flow
- Mermaid diagram
- constraints
- open questions
- implementation boundary notes

For new services, the service template and checklist are the required starting point rather than optional references.

## Constraints

- Treat this as a non-negotiable step for meaningful new work.
- Do not jump straight to implementation for a new service, a new engine/runtime component, or a meaningful architecture change.
- Keep the explanation concrete and repo-relevant.
- Prefer small, readable Mermaid diagrams over large generic ones.
- Align terminology with LinkSmith contracts: services, ports, artifacts, schemas, steps, invocations, edges.
- For new services, align the doc with the required location and sections in `docs/architecture/service-standards.md`.

## Notes

- This skill exists so the design can be reviewed before code is written.
- Pair it with `linksmith-review` later when the implementation exists and needs branch review.
