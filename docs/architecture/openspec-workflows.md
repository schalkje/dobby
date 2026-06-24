# OpenSpec Workflows

OpenSpec is an **external tool** with its own update cycle. Dobby wraps it for convenience but does not manage, configure, or extend the OpenSpec CLI itself.

## Relationship to Dobby

OpenSpec serves as the **main deliverable format for the implementation phase**. The Dobby tracker skills handle work-item management (create, refine, close); OpenSpec handles spec-driven implementation.

The bridge between the two is `dobby-propose-from-pbi` (or its GitHub variant `dobby-gh-propose-from-issue`), which:

1. Reads a refined work item from the tracker (ADO PBI or GitHub Issue)
2. Generates an OpenSpec change directory under `openspec/changes/<name>/`
3. Seeds it with `proposal.md`, `design.md`, and `tasks.md`
4. Adds a traceability line linking back to the source work item

### Change naming conventions

| Backend | Change name format | Traceability line |
|---|---|---|
| Azure DevOps | `pbi-<id>-<slug>` | `> Source: Azure DevOps PBI [#<id>](<url>) — "<title>"` |
| GitHub | `issue-<id>-<slug>` | `> Source: GitHub Issue [#<id>](<url>) — "<title>"` |

## Wrapper skills

### `openspec-propose`

Creates a new change with all artifacts in one step. Use when describing what to build and getting a complete proposal ready for implementation.

### `openspec-apply-change`

Implements tasks from an existing change. Reads task status via `openspec status`, fetches implementation instructions via `openspec instructions`, and updates task checkboxes as work progresses.

### `openspec-explore`

A thinking-only mode — a reasoning partner for exploring ideas, investigating problems, and clarifying requirements. Explicitly non-implementing: it can read, search, and create OpenSpec artifacts, but never writes application code.

### `openspec-archive-change`

Archives a completed change once implementation is finished, moving it to `openspec/changes/archive/YYYY-MM-DD-<name>/`. Validates that all tasks and artifacts are complete before archiving.

## Wrapping pattern

All four OpenSpec skills follow the same pattern:

1. Call `openspec` CLI with `--json` output
2. Interpret the structured response (context, rules, templates, dependencies)
3. Manage artifacts in `openspec/changes/<name>/`
4. Never modify OpenSpec's own config or internals

Key CLI commands used:

```bash
openspec list --json                              # list all changes
openspec status --change "<name>" --json           # check task/artifact status
openspec instructions <artifact-id> --change "<name>" --json  # get implementation instructions
openspec new change "<name>"                       # create a new change
```

## Boundary

The OpenSpec CLI is a **dependency**, not part of Dobby:

- Dobby does not version, package, or distribute OpenSpec
- Dobby does not modify `openspec/config.yaml` beyond initial placeholder setup
- OpenSpec updates are independent of Dobby updates
- If the OpenSpec CLI changes its interface, the wrapper skills need updating — but that's a Dobby maintenance task, not an OpenSpec one
