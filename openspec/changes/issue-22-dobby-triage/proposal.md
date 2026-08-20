# Proposal: dobby-triage — read-only listing/triage front door

> Source: GitHub Issue [#22](https://github.com/schalkje/dobby/issues/22) — "New skill: dobby-triage — read-only listing/triage front door for the lifecycle"

## Why

The lifecycle has create/update/propose/close/implement but no way to survey what already exists. Users start at "create" blind. A read-only triage skill is low-risk, high-frequency, and hands off naturally to the existing skills.

## What changes

- New user-facing skill `dobby-triage` in all three scenarios, declared in `skills/manifest.json`:
  - `github` prose: `gh issue list` / `gh search issues` with `--json`;
  - `ado` prose: `az boards query` (WIQL);
  - `combined` **reuses `ado`** (work items live in ADO).
- Strictly read-only: never creates, edits, comments on, or closes anything.
- Filters: state, label/tag, assignee, free text, result limit.
- Output: compact table (id, title, type/labels, assignee, last-updated, stale flag) plus a suggested next action per item mapped to the existing dobby skills.
- Evals (`evals/evals.json`, github tier) including a pressure eval defending the read-only rule and should-not-trigger prompts.

## Out of scope

- Batch mutations, sprint planning, reporting dashboards (per issue #22).
- Projects v2 board data (tracked separately in issue #23).

## Impact

- `skills/manifest.json`: +1 user-facing skill in all scenarios.
- New dirs: `skills/github/dobby-triage/`, `skills/ado/dobby-triage/`.
- `CLAUDE.md`: user-facing skill list gains `dobby-triage`.
- No `_lib` scripts, no config schema changes.
