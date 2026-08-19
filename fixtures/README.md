# Fixtures

This folder holds machine-checked conformance fixtures for LinkSmith contracts and services.

These are repo fixtures for tests, schema validation, and container verification. They are not treated as real project artifacts or runtime outputs.

Each schema family can contain:

- `valid/`: examples that should validate
- `invalid/`: examples that should fail validation
- `manifest.json`: a small machine-readable index of the schema and example files

The initial layout includes registry, pipeline, artifact, and service fixtures.
