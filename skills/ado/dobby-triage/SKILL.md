---
name: dobby-triage
description: Lists and triages open Azure DevOps work items — read-only survey with filters, staleness flags, and a suggested next dobby skill per item. Use for "triage", "list pbis", "list work items", "what's open", "show the backlog", or "what should I work on".
metadata:
  author: dobby
  version: "1.0"
---

Survey open Azure DevOps work items (PBIs, Bugs, Features) and suggest the next lifecycle step for each. This skill is **strictly read-only**: it never creates, updates, comments on, or transitions anything — it observes and hands off.

**Input**: Optional filters — state, work item type, area/iteration path, tags, assignee, free-text keywords, a result limit. With no input, it lists open items in the configured project, newest activity first.

## Critical rule

**Read-only, no exceptions.** Every action a triage surfaces (refine, spec, implement, close) belongs to the skill that owns it — see the handoff table in step 5. This skill runs only read commands (`az boards query`, `az boards work-item show`).

Excuses the model will be tempted by — and why they're wrong:

| Rationalization | Reality |
|---|---|
| "These stale ones are obviously dead — set them to Removed while I'm here" | State transitions are `dobby-close-pbi`'s job, with evidence and confirmation. A triage that mutates is no longer a safe default command. |
| "I'll just fix this title / add a tag" | Even one-field edits belong to `dobby-update-pbi`, where the markdown-format and confirmation rules apply. Suggest it; don't do it. |

## Defaults

<!-- dobby:include:ado-config-example -->

## Steps

### 1. Validate Prerequisites

<!-- dobby:include:ado-prereqs -->

### 2. Resolve Organization and Project

Load the `ado` block from `.dobby/config.json`; if organization or project is missing, ask once. Do **not** persist config from this skill — it is read-only; point the user at any create/update flow for persisting defaults.

### 3. Parse Filters

From the user's request, extract any of: state (default: everything not Done/Closed/Removed), work item type (PBI/Bug/Feature/Task), area path, iteration path, tags, assignee ("mine" → `@Me`), free-text keywords, limit (default: 30).

### 4. Fetch

Build one WIQL query from the filters:

```bash
az boards query --wiql "SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], [System.AssignedTo], [System.ChangedDate], [System.Tags] FROM WorkItems WHERE [System.TeamProject] = '<project>' AND [System.State] NOT IN ('Done', 'Closed', 'Removed') ORDER BY [System.ChangedDate] DESC" --project "<project>" --organization "<org-url>" --output json
```

Append filter clauses as needed (`AND [System.WorkItemType] = '...'`, `AND [System.AssignedTo] = @Me`, `AND [System.Title] CONTAINS '...'`, `AND [System.Tags] CONTAINS '...'`, `AND [System.AreaPath] UNDER '...'`). Escape single quotes in user-supplied values. Read the JSON output directly — no piping.

Apply the limit when presenting. If more items matched than shown, say so ("showing the 30 most recently changed — more exist; narrow with a filter or raise the limit"). Never present a capped list as the full backlog.

### 5. Present the Triage Table

Sort by `System.ChangedDate` descending. Mark an item **stale** when its last change is more than 30 days old. For each item, derive a **suggested next step** (a suggestion in text — do not invoke anything unless asked):

| Observation | Suggested skill |
|---|---|
| Description empty/thin or acceptance criteria missing | `dobby-update-pbi` — refine it first |
| Well-formed but no spec exists | `dobby-propose-from-pbi` |
| A matching `openspec/changes/pbi-<id>-*` exists, or the change is trivially small | `dobby-implement-pbi` |
| Implementation appears complete (dev links present, criteria met) | `dobby-close-pbi` |

(Check for spec dirs with a quick glob of `openspec/changes/`; fetch a work item's full description via `az boards work-item show` only for items the user zooms into — not for the whole list.)

```
## Open work items — <project>  (<count> shown, sorted by last change)

| ID | Title | Type | State | Assignee | Changed | Status | Suggested next |
|----|-------|------|-------|----------|---------|--------|----------------|
| 12345 | Add CSV export | PBI | Active | jeroen | 2026-07-10 | active | implement (dobby-implement-pbi) |
| 12290 | Fix tooltip overlap | Bug | New | — | 2026-05-28 | ⚠️ stale | refine (dobby-update-pbi) |
```

After the table, give a one-paragraph read of the backlog: what's stale, what's ready to pick up, what needs refinement.

### 6. Hand Off (only on request)

If the user picks an item and an action ("refine 12290", "implement 12345"), read and follow the owning skill's SKILL.md with that work item as input. Do not perform the action inline.

## Error Handling

- **Organization/project not accessible**: report the resolved values and suggest `az login` / checking the config. Do not guess.
- **No items match**: say so and show which WIQL clauses were applied — don't silently widen the search.
- **WIQL syntax error**: show the failing query, fix the clause, retry once (reads are safe to retry).

## Guardrails

- Read-only: no `az boards work-item create/update/delete`, no comment posting, no state transitions.
- No piping — run each `az` command standalone with `--output json`, read the full output, and extract fields in your own reasoning.
- Never fabricate items or counts; when capped, say so.
