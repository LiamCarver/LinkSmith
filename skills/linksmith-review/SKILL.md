---
name: linksmith-review
description: "Review local LinkSmith branches when the task is a PR review, branch review, or change review for this repository and the reviewer should apply LinkSmith's contract-first, deterministic-first standards."
---

# Linksmith Review

Use this skill when reviewing LinkSmith changes. The goal is to produce a high-signal review focused on contracts, schema integrity, deterministic-vs-LLM choices, and validation quality.

## Workflow

1. Run `scripts/review-branch.ps1` when local source and target branches are available.
2. Read:
   - `docs/engineering/python-standards.md`
   - `docs/engineering/pr-review.md`
3. Review findings in this order:
   - contract correctness
   - schema compatibility
   - type safety
   - deterministic vs LLM appropriateness
   - failure handling
   - tests and fixture coverage
   - documentation alignment

## Review Priorities

- Treat registry, pipeline, and artifact schema changes as high-sensitivity changes.
- Prefer findings about broken contracts, drift, unsafe typing, or missing validation over style commentary.
- Call out any case where deterministic code should replace AI behavior.
- Check that example fixtures remain aligned with schema changes.
- Check that JSON boundary handling is validated early and outputs are validated before writing.

## Output Shape

- Findings first, ordered by severity.
- Include file references where possible.
- If there are no findings, say so explicitly and mention residual risk or missing coverage.

## Notes

- The default review path is local branch vs local branch in this repo.
- Use `-FetchFirst` only when the user explicitly wants remote updates pulled in before the review.
- Use the branch review script output as the main diff input when available.
- Do not expand the review into unrelated refactors or implementation proposals unless they directly explain a finding.
