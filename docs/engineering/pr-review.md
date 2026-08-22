# PR Review Guide

## Purpose

This guide is for reviewing LinkSmith branches consistently, including in fresh Codex sessions.

The primary review lens is not style. It is contract integrity and execution safety.

## Review Order

Review changes in this order:

1. Contract correctness
2. Schema compatibility
3. Type safety
4. Deterministic vs LLM appropriateness
5. Failure handling
6. Tests and example coverage
7. Documentation updates

## What To Look For

### 1. Contract Correctness

- Did the registry contract change?
- Did the pipeline contract change?
- Did artifact schemas change?
- Are example fixtures still aligned?

### 2. Schema Compatibility

- Are new required fields justified?
- Are old examples or services broken by the change?
- Are input and output ports still coherent?

### 3. Type Safety

- Are raw dictionaries confined to the edges?
- Are internal models typed?
- Are public functions and service entrypoints annotated?

### 4. Deterministic First

- Is an LLM being used where deterministic code would be better?
- Is rendering deterministic?
- Are structural transforms staying out of LLM prompts?

### 5. Failure Handling

- Are validation failures explicit?
- Are retries/recovery paths sensible?
- Are useful artifacts preserved for debugging?

### 6. Tests And Fixtures

- Are there valid and invalid examples where relevant?
- Are deterministic changes covered by unit tests?
- Are schema changes reflected in fixture updates?

### 7. Docs

- Do standards/spec docs still match implementation intent?
- Do examples still teach the right mental model?

## Expected Review Output

A good review should prioritize findings such as:

- broken contracts
- schema drift
- unsafe typing
- misuse of LLMs
- missing validation
- missing tests

If no findings are present, call that out explicitly and mention residual risk or missing coverage.

## Ref Comparison Workflow

Use the review helper script in `scripts/review-branch.ps1` to produce:

- ref metadata
- merge base
- commit list
- changed files
- diff stat
- patch output

This should be the default input to a fresh review session.

The script now supports any local Git refs that resolve to commits:

- branch vs branch
- tag vs branch
- commit vs branch

Examples:

```powershell
.\scripts\review-branch.ps1 -SourceRef main -TargetRef engine-mvp-1
.\scripts\review-branch.ps1 -SourceRef main -TargetRef ec300ef
.\scripts\review-branch.ps1 -SourceBranch main -TargetBranch main~3
```

Notes:

- `SourceBranch` and `TargetBranch` still work as backward-compatible aliases.
- The script resolves both refs to commits before producing the diff.
- `-FetchFirst` is still optional and should only be used when the user explicitly wants remote updates fetched before review.
