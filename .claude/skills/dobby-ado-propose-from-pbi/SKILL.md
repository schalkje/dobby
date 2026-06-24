---
name: dobby-ado-propose-from-pbi
description: Internal — creates an OpenSpec proposal from an Azure DevOps PBI. Invoked by dobby-propose-from-pbi after backend resolution. Do not invoke directly unless forcing the ADO backend. Fetches work item details and generates proposal, design, and task artifacts ready for implementation.
metadata:
  author: dobby
  version: "2.0"
---

<!-- This file is a copy of `skills/dobby-ado-propose-from-pbi/SKILL.md` — edit the source, not this copy. Regenerate with `python scripts/sync-skills.py`. -->

Create an OpenSpec change proposal from an existing Azure DevOps Product Backlog Item.

This skill is the **Azure DevOps implementation** invoked by the `dobby-propose-from-pbi` dispatcher after it resolves `backend: "ado"` from `.dobby/config.json`. Direct invocation is supported as an escape hatch.

**Input**: A PBI identifier — work item number, title/keywords, `AB#12345` reference, or a full Azure DevOps work item URL.

## Defaults

Read the `ado` block from `.dobby/config.json` in the repository root. Example shape:

```json
{
  "backend": "ado",
  "ado": {
    "organization": "https://dev.azure.com/myorg/",
    "project": "MyProject",
    "team": "MyTeam"
  }
}
```

The values under `ado` eliminate repeated prompts for org and project. If the `ado` block is missing or incomplete, collect the missing fields interactively (same pattern as `dobby-ado-create-pbi`).

## Steps

### ⛔ Command Execution Rules

- **No piping.** Every `az` and `python` command in this skill is designed to be run standalone with `--output json`. Do NOT append any pipe (`|`) to transform, filter, or format the output — no `| ConvertFrom-Json`, `| Select-Object`, `| jq`, `| python -c "..."`, `| grep`, or any other pipe. Read the full JSON output and extract fields in your own reasoning.
- **Use canonical `skills/` paths.** Reference scripts and templates from the canonical `skills/` directory — e.g., `python skills/dobby-ado-create-pbi/scripts/azdo-update-fields.py`, not from `.github/skills/` or `.claude/skills/` host copies.

### 1. Validate Prerequisites

Run these checks in parallel where possible.

**1a. Check Azure CLI and DevOps extension**
```bash
az version --output json
```
- If `az` is not found → stop: "Azure CLI is not installed. Install from https://learn.microsoft.com/cli/azure/install-azure-cli"
- If `azure-devops` extension is not in the output → stop: "Run: `az extension add --name azure-devops`"

**1b. Check OpenSpec CLI**
```bash
openspec --version
```
- If `openspec` is not found → stop: "OpenSpec CLI is required. Install it first."

**1c. Check authentication**
```bash
az account show --query "{user:user.name, tenant:tenantId}" --output json
```
- If this fails → stop: "Run: `az login`"
- Display the logged-in user so they can confirm the right account.

### 2. Resolve Organization and Project

**2a.** Load the `ado` block from `.dobby/config.json` if it exists, merge with `az devops configure --list` (file takes priority).

**2b.** If organization is unknown, ask the user.

**2c.** Validate Azure DevOps access:
```bash
az devops project list --organization "<org-url>" --output json
```
- If this fails → stop: "Cannot access this organization with the current account. Run `az login` to switch."

**2d.** If project is unknown, present available projects and ask.

### 3. Find the PBI

Parse the user's input to determine the lookup strategy:

| Input format | Strategy |
|---|---|
| Numeric ID (e.g., `12345`) | Direct fetch |
| `AB#12345` | Extract numeric ID, direct fetch |
| Azure DevOps URL (`.../_workitems/edit/12345`) | Extract numeric ID, direct fetch |
| Title or keywords | WIQL search |

**3a. Direct fetch by ID**
```bash
az boards work-item show --id <id> --organization "<org-url>" --output json
```
- If not found → stop: "Work item <id> does not exist or is not accessible."
- If the work item belongs to a different project than configured, warn but continue.

**3b. Search by title/keywords**
```bash
az boards query --wiql "SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State] FROM WorkItems WHERE [System.TeamProject] = '<project>' AND [System.Title] CONTAINS '<keywords>' AND [System.State] <> 'Removed' ORDER BY [System.ChangedDate] DESC" --project "<project-name>" --organization "<org-url>" --output json
```

- Escape single quotes in keywords for WIQL.
- Do not hard-code work item type — search across PBI, User Story, Requirement, etc.
- Prefer active/open items (show state in results).
- If multiple matches → present a selection list with ID, title, type, and state. Ask the user to confirm.
- If no matches → suggest broadening the search or entering an ID directly.

### 4. Extract PBI Details

From the fetched work item, extract these fields:

| Field | API field | Required |
|---|---|---|
| Title | `System.Title` | Yes |
| Description | `System.Description` | No |
| Acceptance Criteria | `Microsoft.VSTS.Common.AcceptanceCriteria` | No |
| State | `System.State` | Yes |
| Work Item Type | `System.WorkItemType` | Yes |
| Tags | `System.Tags` | No |
| Area Path | `System.AreaPath` | No |
| Iteration Path | `System.IterationPath` | No |

**HTML normalization**: Azure DevOps fields often contain HTML. Before using as context:
- Strip HTML tags, converting to clean Markdown/plain text.
- Preserve links, lists, and table structures where possible.
- Handle HTML entities (`&amp;`, `&lt;`, etc.).

**If Description and Acceptance Criteria are both empty**, warn the user:
> "This PBI has no description or acceptance criteria. I can still generate a proposal, but the spec will be based on the title alone. Want to continue, or add context first?"

**If the PBI is Closed/Done**, ask before proceeding:
> "This PBI is marked as <state>. Do you still want to generate a spec for it?"

### 5. Fetch Related Context (bounded)

**5a. Parent work item** (always, if present)

Check the work item's relations for a parent link. If found:
```bash
az boards work-item show --id <parent-id> --organization "<org-url>" --output json
```
Extract the parent's title, type (Feature/Epic), and description summary.

**5b. Direct children** (optional, capped)

Check relations for child links. If present:
- If ≤ 5 children, fetch their titles and states.
- If > 5 children, show count and ask: "This PBI has <N> child items. Fetch summaries?"
- Include as "Additional context" in the spec, not as hard requirements.

**5c. Related links** (optional, capped)

Check relations for related/predecessor/successor links:
- If ≤ 5 related items, fetch their titles.
- If > 5, show count and ask before fetching.
- Include as context only.

### 6. Refine the PBI

Before generating the spec, analyze the PBI for gaps, ambiguities, or missing details. Ask the user refinement questions to sharpen the requirements.

**6a. Identify gaps**

Review the PBI description, acceptance criteria, and the codebase context gathered in steps 4-5. Look for:
- Ambiguous scope (e.g., "remove code field" — from which views exactly?)
- Missing behavioral decisions (e.g., keep derivation logic or remove it?)
- Edge cases not covered in acceptance criteria
- Implicit assumptions that should be explicit

**6b. Ask refinement questions**

Present refinement questions to the user using a structured form. Group related questions logically. Provide sensible defaults where possible.

Example questions:
- Exact tooltip text for a UI label change
- Whether to keep/remove background logic when hiding a field
- Which views/pages are affected
- Behavioral choices for edge cases

**6c. Write refinements back to the PBI**

After the user answers (or if running autonomously, after making reasonable decisions), **update the PBI in Azure DevOps** with the refined content:

- Update **Description** (`System.Description`) — expand the scope section with the decisions made
- Update **Acceptance Criteria** (`Microsoft.VSTS.Common.AcceptanceCriteria`) — add new criteria based on refinement answers
- Add a **Refinement Notes** section to the description capturing the decisions and rationale

Use the helper script at `skills/dobby-ado-create-pbi/scripts/azdo-update-fields.py` to update fields as Markdown:

```bash
python skills/dobby-ado-create-pbi/scripts/azdo-update-fields.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --field "System.Description=<path-to-desc.md>" \
    --field "Microsoft.VSTS.Common.AcceptanceCriteria=<path-to-ac.md>"
```

This ensures the PBI stays the source of truth — the spec is generated from the *refined* PBI, and the refinements are durable in Azure DevOps.

### 7. Confirm Before Generating

Present a summary of what will be used to generate the spec:

```
## Proposal Context

- **PBI**: #12345 — "Add login page" [Active, Product Backlog Item]
- **Description**: <summary or "empty">
- **Acceptance Criteria**: <summary, including refinements>
- **Parent**: Feature #9876 — "Modernize customer portal" (or "none")
- **Related items**: <count> items included as context
- **Proposed change name**: pbi-12345-add-login-page
- **Refinements applied**: <count> questions answered, PBI updated

Proceed?
```

Wait for user confirmation. A simple "yes" should suffice.

### 8. Create OpenSpec Change

**8a. Derive change name**

Generate a kebab-case name from the PBI:
- Format: `pbi-<id>-<title-slug>` (e.g., `pbi-12345-add-login-page`)
- Truncate the title slug to keep the name reasonable (≤ 50 chars total).

**Check for existing change**:
- If `openspec/changes/<name>/` already exists, ask:
  1. Continue/update that change
  2. Create with a different name
  3. Abort

**8b. Create the change**
```bash
openspec new change "<name>"
```

**8c. Get artifact build order**
```bash
openspec status --change "<name>" --json
```
Parse the JSON for `applyRequires` and the list of artifacts with their dependencies.

**8d. Generate artifacts in dependency order**

Loop through artifacts whose dependencies are satisfied:

1. Get instructions:
   ```bash
   openspec instructions <artifact-id> --change "<name>" --json
   ```

2. Read any completed dependency artifact files for context.

3. **Inject PBI context**: When generating each artifact, use the fetched PBI details as the primary input:
   - **proposal.md**: Use the PBI title as the change title, description as the problem/motivation, acceptance criteria as success criteria, parent feature as broader context.
   - **design.md**: Use acceptance criteria and description to inform design decisions and constraints.
   - **tasks.md**: Break down acceptance criteria into implementable tasks.

4. Use the `template` from instructions as the structure. Apply `context` and `rules` as constraints — do NOT copy them into the output.

5. Write the artifact file to `outputPath`.

6. Re-check status:
   ```bash
   openspec status --change "<name>" --json
   ```

7. Continue until all `applyRequires` artifacts are complete.

### 9. Add Traceability

**9a. Record source in proposal.md**

Include a "Source" section at the top of `proposal.md` (or wherever appropriate per template):

```markdown
> Source: Azure DevOps PBI [#12345](https://dev.azure.com/...) — "Add login page"
```

This makes the link durable regardless of whether the PBI is updated.

**9b. Offer to link back to the PBI** (opt-in)

After successful spec creation, ask:
> "Would you like me to add a comment to PBI #12345 linking to this OpenSpec change?"

If yes, add a discussion comment via `az boards work-item update` or the REST API:
```
OpenSpec change created: `pbi-12345-add-login-page`
Artifacts: proposal.md, design.md, tasks.md
```

Do not update automatically — respect team conventions.

### 10. Show Final Status

```bash
openspec status --change "<name>"
```

Present a summary:

```
## ✓ OpenSpec Proposal Created from PBI #12345

- **Change**: pbi-12345-add-login-page
- **Location**: openspec/changes/pbi-12345-add-login-page/
- **Artifacts created**:
  - proposal.md — what & why
  - design.md — how
  - tasks.md — implementation steps
- **Source PBI**: #12345 — "Add login page"

Ready for implementation! Run `/opsx:apply` or ask me to implement.

### Recommended branch
If not already on a feature/fix branch:
- Bug: `fix/<id>-<slug>`
- PBI/Feature: `feat/<id>-<slug>`
```

**Note on branching**: This skill does not create or switch branches — that is the responsibility of the caller (typically `dobby-implement-pbi`). The branch recommendation is informational only.

## Error Handling

- **Wrong identity**: If `az devops project list` fails, show current identity and suggest `az login`.
- **PBI not found**: Clear message with the ID/keywords used.
- **PBI inaccessible**: Suggest checking permissions or organization.
- **HTML content issues**: Warn if normalization fails, proceed with best-effort.
- **Empty PBI fields**: Warn and ask for additional context before generating.
- **WIQL failures**: Escape special characters, retry with broader query if needed.
- **OpenSpec CLI failure**: Report the failing command and suggest manual retry.
- **Partial success**: If some artifacts are created but not all, report what succeeded and what failed. The user can re-run artifact generation.
- **PBI update failure**: Report partial success — the spec is created, only the PBI link failed. Provide the manual command.

## Guardrails

- Always show the logged-in identity early so the user can catch wrong-account issues.
- Do not hard-code work item type — accept PBI, User Story, Requirement, etc.
- Normalize HTML fields before using as spec context.
- Include PBI number in change name for traceability.
- Bound related-item fetching — parent always, children/links capped at 5.
- Do not update the PBI automatically — always ask first.
- Escape special characters in WIQL queries.
- Use `--output json` on all `az` commands for reliable parsing.
- Include `--organization` on all commands unless a confirmed default exists.

## Optional Quality Gate

After successful proposal generation, suggest:

> **Optional quality gates before implementation:**
> - Run `grill-proposal` to challenge the scope, goals, and feasibility of the proposal.
> - Run `grill-design` to stress-test the architecture, trade-offs, and implementation risks.

Do not invoke these automatically — only suggest them. The user decides whether to grill.

## Usage Examples

**By PBI number:**
> Create a spec for PBI 12345

**By AB# reference:**
> Create a spec for AB#12345

**By URL:**
> Create a spec for https://dev.azure.com/myorg/MyProject/_workitems/edit/12345

**By title/keywords:**
> Create a spec for the "login page" PBI

**Minimal:**
> Spec from PBI 12345
