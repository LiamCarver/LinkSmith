# Registry Spec Notes

## Purpose

The registry is the source of truth for which services LinkSmith can invoke.

Each registry entry describes:

- what the service is
- what it accepts
- what it emits
- how each port behaves
- whether it is deterministic or LLM-backed
- where the engine should invoke it
- what config shape it expects

This is intended to let the engine validate pipelines before execution.

## Why Start Here

The registry is the narrowest stable contract in the system.

Before defining pipelines, the engine needs a clear answer to:

- what services exist
- what types can flow between them
- what step contracts are valid

## v1 Design

The initial registry model is intentionally small:

- top-level registry file with a `services` array
- each service has a stable `id`
- each service declares:
  - `kind`
  - `deterministic`
  - `description`
  - `entrypoint`
  - `inputs`
  - `outputs`
  - per-port `mode`
  - per-port `cardinality`
  - optional `configSchema`
  - optional `notes`

## Service Kinds

The first supported service kinds are:

- `transform`
- `render`
- `ingest`
- `export`

These are descriptive categories, not execution backends.

## Artifact Types

Artifact types are string labels for now. Examples:

- `application/json`
- `text/markdown`
- `image/png`
- `application/vnd.obsidian.canvas+json`

This can evolve later into a stricter type model if needed.

## Port Semantics

Each port now carries extra specificity:

- `name`
- `type`
- `mode`
- `cardinality`

`mode` describes how the artifact is treated:

- `file`
- `directory`
- `artifact-ref`

`cardinality` describes whether the service expects or emits:

- `one`
- `many`

This is required because LinkSmith needs to support:

- deterministic converters such as canvas -> JSON
- folder-based LLM summarizers
- synthesis services that accept arrays of prior artifacts
- services that emit more than one artifact

## Deterministic Flag

`deterministic` is an explicit boolean.

This exists because LinkSmith should preserve a strong architectural rule:

- if a transformation can be done exactly with code, prefer that over an LLM

The engine can later use this field for validation, recommendations, or execution policy.

## Open Questions

- Should `entrypoint` be a structured object instead of a string in v1?
- Should registry entries declare version compatibility with the engine?
- Should a service declare whether it is safe for caching or memoization?
