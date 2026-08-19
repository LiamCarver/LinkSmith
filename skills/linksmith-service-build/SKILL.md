---
name: linksmith-service-build
description: "Build a new LinkSmith service after design approval using realistic fixtures, a red high-fidelity test, and a container-first implementation workflow."
---

# Linksmith Service Build

Use this skill when the task is to implement a new LinkSmith service after its design has already been reviewed.

This skill does not replace the design-first workflow. For meaningful new services, the design documentation must already exist and be reviewed before implementation starts.

## Goal

Implement new LinkSmith services in a way that keeps the workflow:

- design-first
- fixture-driven
- high-fidelity test-driven
- container-first

## Required Inputs

Before implementation, confirm that the service already has:

- a reviewed design doc under `docs/components/services/` or another approved `docs/components/` path
- realistic fixture expectations
- a clear input and output contract

If those are missing, stop implementation work and follow the existing `linksmith-design-docs` workflow first.

## Required Workflow

For a new service, the default implementation shape is:

1. confirm the design doc is present and reviewed
2. create realistic fixtures under `fixtures/services/<service-id>/`
3. add or update reusable artifact fixtures under `fixtures/artifacts/` when relevant
4. add a red high-fidelity test
5. scaffold the service CLI and container entrypoint
6. run the red test and confirm the failure is meaningful
7. implement the service logic
8. rerun local and container tests until green
9. record what `linksmith-core` helped with and what friction appeared

## References

Read these before implementing:

- `docs/engineering/service-build-workflow.md`
- `docs/checklists/new-service-checklist.md`

For the mandatory design-first step and design-doc requirements, also use:

- `skills/linksmith-design-docs/SKILL.md`

## Constraints

- Prefer deterministic implementations when exact code can do the transform.
- Treat realistic fixtures as part of the service contract, not as optional extras.
- Prefer at least one container-level high-fidelity test for new services.
- Compare JSON outputs structurally rather than by brittle string formatting unless formatting is itself the contract.
- Keep service-specific logic separate from container/runtime plumbing where practical.

## Notes

- This skill exists to standardize the service-build loop before the engine is implemented.
- It should make future deterministic conformance checking easier because the workflow is explicit and repeated.
