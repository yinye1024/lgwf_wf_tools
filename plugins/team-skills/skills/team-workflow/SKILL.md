---
name: team-workflow
description: Apply shared team development workflow conventions in Codex. Use when starting code changes, reviewing or preparing delivery, adding team skills, deciding verification scope, or when the user asks to follow team standards, team workflow, repository conventions, PR readiness, or handoff expectations.
---

# Team Workflow

## Overview

Use this skill as the team's default operating guide for Codex development tasks. It keeps execution consistent while leaving repository-specific implementation decisions to the codebase.

## Workflow

1. Inspect the repository state before editing.
   - Check current branch and dirty files.
   - Read nearby code and tests before deciding an implementation shape.
   - Treat unrelated changes as user-owned.

2. Choose the smallest coherent change.
   - Follow existing project patterns, naming, structure, and tooling.
   - For new or rewritten human-facing Markdown and docs, follow `references/team-conventions.md` Content Language Defaults: body text defaults to Chinese unless the user asks otherwise.
   - Add abstractions only when they remove real duplication or clarify shared behavior.
   - Avoid broad refactors unless they are necessary for the requested outcome.

3. Verify with evidence.
   - Run focused tests or checks that exercise the changed behavior.
   - If a full suite is expensive, run the relevant subset and say what was not run.
   - For frontend changes, inspect the app visually when a local target is available.

4. Hand off clearly.
   - State what changed, where it changed, and how it was verified.
   - Mention any residual risk, skipped verification, or environment blocker.
   - Keep the final response concise and actionable.

## References

- Read `references/team-conventions.md` when the user asks about team defaults, content language rules, adding more team skills, delivery checklist details, or reusable policy text.
