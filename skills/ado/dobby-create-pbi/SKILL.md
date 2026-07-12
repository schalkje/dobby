---
name: dobby-create-pbi
description: Creates a PBI (or Feature, when hierarchy requires it) in Azure DevOps. Collects fields interactively, validates prerequisites, and creates the work item via the az boards CLI.
metadata:
  author: dobby
  version: "3.0"
---

Create a Product Backlog Item (PBI) — and when needed, a parent Feature — in Azure DevOps from a conversational request.


**Input**: The user may provide any combination of: title, description, project, area path, iteration, parent work item (ID or keywords). Any missing required fields are collected interactively.

## ⛔ Critical Rules (read before every run)

These rules prevent the most common and costly mistakes. Violating any one produces broken work items that require manual cleanup.

1. **NEVER use `--description` on `az boards work-item create` or `az boards work-item update`.** It truncates at the first newline. Always use the helper script (`azdo-update-fields.py`) for `System.Description` and `Microsoft.VSTS.Common.AcceptanceCriteria`.
2. **NEVER write HTML in description or acceptance criteria fields.** Content must be **Markdown** — not HTML. No `<b>`, `<br>`, `<ul>`, `<li>` tags. Use markdown syntax: `**bold**`, line breaks, `- list items`. The helper script sets the field format to Markdown; HTML content in a Markdown-formatted field renders as raw escaped tags.
3. **ALWAYS follow the template** when generating description and acceptance criteria. PBIs use `templates/pbi-template.md`; Features use `templates/feature-template.md`. Do not invent ad-hoc formats.
4. **NEVER use `--parent` on PBI or Feature creation.** The `--parent` flag only works for `--type Task`. For PBIs and Features, create the item first, then link with: `az boards work-item relation add --id <new-id> --relation-type parent --target-id <parent-id>`.
5. **NEVER create a PBI under another PBI.** ADO hierarchy is strict — see the hierarchy section below. A PBI's parent must be a Feature.
6. **Always create items as `--type "Product Backlog Item"`.** Do not use `--type Task` unless explicitly creating a Task (a sub-work-item of a PBI).
7. **Always use the helper script for multiline fields** — both on create and on update. `az boards` cannot set markdown format.
8. **Run commands exactly as shown — no piping, no post-processing.** Every `az` and `python` command in this skill is designed to be run standalone with `--output json`. Do NOT append any pipe (`|`) to transform, filter, or format the output. This includes `| ConvertFrom-Json`, `| Select-Object`, `| jq`, `| python -c "..."`, `| grep`, or any other pipe. Read the full JSON output and extract fields in your own reasoning.
9. **Resolve bundled files relative to the installed skill set.** Scripts ship under their owning skill's `scripts/` folder and templates under this skill's `templates/` folder — e.g., `python skills/_lib/azdo-update-fields.py` and `templates/pbi-template.md`. Never reach back into dobby's source repository for them.

## ADO Work Item Hierarchy

In this project/process, Azure DevOps enforces a strict parent-child hierarchy:

```
Epic → Feature → Product Backlog Item (PBI) → Task
```

**Rules:**

| Child type | Valid parent type | Invalid parent types |
|---|---|---|
| Task | PBI | Feature, Epic, Task, another PBI |
| PBI | Feature | PBI, Epic, Task |
| Feature | Epic (or no parent) | Feature, PBI, Task |

**Consequences of violating hierarchy:**
- ADO may accept the link but reports, boards, and backlog views will break or hide items.
- Sprint planning, velocity tracking, and rollup calculations depend on correct hierarchy.

### Starting from an Existing Work Item

When the user references an existing work item (e.g., "create PBIs under #1013607"), **always inspect it before creating children**:

```bash
az boards work-item show --id <id> --expand Relations --organization "<org-url>" --output json
```

Extract:
- **Type**: `fields["System.WorkItemType"]`
- **Parent**: find the relation with `rel: "System.LinkTypes.Hierarchy-Reverse"` — the parent ID is the last segment of its `url` field

Then use this decision table:

| Existing item type | User wants | Action |
|---|---|---|
| **Feature** | child PBIs | ✅ Create PBIs under this Feature |
| **PBI** with Feature parent | sibling PBIs | ✅ Create PBIs under the same parent Feature |
| **PBI** without Feature parent | multiple PBIs | 🔨 Create a new Feature first, move original PBI under it, then create sibling PBIs |
| **PBI** without Feature parent | single PBI | 🔨 Create a new Feature, parent both PBIs under it |
| **Task** | PBIs | Navigate up: use the Task's parent PBI's parent Feature. Create PBIs there. |
| **Epic** | PBIs | Create a Feature under the Epic, then PBIs under the Feature |

**When you need to create a Feature** (see the "Creating a Feature" section below for the full workflow):
1. Create the Feature work item
2. Link it to the appropriate parent (Epic, if one exists in the chain)
3. If an existing PBI needs to become a child of the new Feature, re-parent it:
   ```bash
   # If the PBI had an old parent, remove that link first:
   az boards work-item relation remove --id <pbi-id> --relation-type parent --target-id <old-parent-id> --yes --organization "<org-url>"
   # Then add the new Feature as parent:
   az boards work-item relation add --id <pbi-id> --relation-type parent --target-id <feature-id> --organization "<org-url>"
   ```
4. Then create the new PBIs under the Feature

**Always confirm the proposed hierarchy with the user** via `ask_user` before creating work items. Show the planned structure.

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

The values under `ado` eliminate repeated prompts. If the `ado` block is missing or incomplete, the missing fields will be collected during the first run and persisted at the end (step 7).

## Steps

### 1. Validate Prerequisites

Run these checks in parallel where possible.

**1a. Check Azure CLI and extension**
```bash
az version --output json
```
- If `az` is not found → stop: "Azure CLI is not installed. Install from https://learn.microsoft.com/cli/azure/install-azure-cli"
- If `azure-devops` is not listed under `extensions` → install it: `az extension add --name azure-devops`
  - Symptom that the extension is missing: any `az devops ...` or `az boards ...` command fails with `'devops' is misspelled or not recognized by the system.`
  - On corporate networks the install may fail with `SSL: CERTIFICATE_VERIFY_FAILED` (self-signed certificate in chain — typical for TLS-inspecting proxies).
    - **Preferred fix**: point Python/`az` at a CA bundle that includes the corporate root certificate. Set these env vars (User scope on Windows, or in the user's shell rc):
      - `REQUESTS_CA_BUNDLE` = `<path-to-cacert.pem>`
      - `AZURE_CLI_CA_BUNDLE` = `<path-to-cacert.pem>`
      - `SSL_CERT_FILE` = `<path-to-cacert.pem>`
      - The bundle should be `certifi`'s `cacert.pem` with the corporate root certificate appended.
      - Verify with: `az devops project list --organization <org-url> --output json` (no SSL bypass needed).
    - **Last-resort workaround** (insecure, only if no bundle is available yet): `AZURE_CLI_DISABLE_CONNECTION_VERIFICATION=1`. This disables TLS verification — use only to unblock and then switch to the CA bundle approach.

**1b. Check Python availability**
```bash
python --version
```
- If `python` is not found → stop: "Python 3 is required for the markdown field helper script. Install from https://python.org"
- Only stdlib is needed — no pip packages required.

**1c. Check authentication and show identity**
```bash
az account show --query "{user:user.name, tenant:tenantId}" --output json
```
- If this fails → stop: "Run: `az login`"
- Display the logged-in user to the user so they can confirm it's the right account.

### 2. Resolve Organization, Project, and Team

**2a. Load defaults**
- Read the `ado` block from `.dobby/config.json` if it exists.
- Also check `az devops configure --list` for CLI-level defaults.
- Merge: file defaults take priority over CLI defaults.

**2b. Determine organization**
- If known from defaults or user input, use it.
- Otherwise, ask the user for their Azure DevOps organization URL.

**2c. Validate Azure DevOps access early**

This is critical — validates that the current identity actually has ADO access:
```bash
az devops project list --organization "<org-url>" --output json
```
- If this fails → stop: "Cannot access this Azure DevOps organization with the current account (<user>). Run `az login` to switch accounts if needed."
- Parse the project list.

**2d. Determine project**
- If known from defaults or user input, validate it exists in the project list.
- Otherwise, present available projects and ask.

**2e. Determine team**

Do NOT assume the team name is `<project> Team`. List actual teams:
```bash
az devops team list --project "<project-name>" --organization "<org-url>" --output json
```
- If known from defaults, validate it exists in the team list.
- If only one team exists, use it automatically.
- Otherwise, present available teams and ask the user to select.

### 3. Collect PBI Fields

**If the user already provided a value for any field, use it directly without prompting or listing.** Only prompt for fields that are missing.

Collect all missing fields in a single prompt where possible (batch into one ask_user call).

**3a. Title** (required)
- If not provided, ask for one.

**3b. Description and Acceptance Criteria** (optional but recommended)

> ⚠️ **All content must be Markdown — never HTML.** Do not use `<b>`, `<br>`, `<ul>`, `<li>`, or any HTML tags. Use standard markdown: `**bold**`, `---` for horizontal rules, `- item` for lists, blank lines for paragraphs.

> ⚠️ **Always follow the template structure.** Read the template file first, then populate each section. Do not invent an ad-hoc format.

Generate content following the template in `templates/pbi-template.md` (bundled with this skill). The template defines two Azure DevOps fields, both stored as **Markdown**:

**Description** (`System.Description`) — populate with:
- User story in `> **As** [role] **of** [system], **I want** ..., **so that** ...` format
- Overview table (Stakeholder, SME, Impact Assessment)
- Goal section
- Scope (In scope / Out of scope)
- Dependencies, Solution Approach, References

**Acceptance Criteria** (`Microsoft.VSTS.Common.AcceptanceCriteria`) — populate with:
- Given/When/Then criteria as checkbox items
- No heading — just the criteria list directly

Do **not** include headings like `## 📝 Description` or `## ✔️ Acceptance Criteria` — the field name in Azure DevOps already serves that purpose.

If the user provides enough context, generate both fields from their input. If not, ask if they want to add details.

**For Features**, use `templates/feature-template.md` instead. Features have a lighter description (outcome, scope, child PBI list) and do NOT use acceptance criteria.

**3c. Area path**
- If the user provided an area path, **trust it** — do not validate against a listing first. Just use it in the create command. If creation fails due to invalid path, then re-prompt.
- If the user did NOT provide an area path:
  ```bash
  az boards area team list --team "<team>" --project "<project-name>" --organization "<org-url>" --output json
  ```
  - Present available paths and ask the user to select one.
  - Also allow free-text entry.

**3d. Iteration**
- If the user provided an iteration, **trust it** — use it directly.
- If the user did NOT provide an iteration:
  ```bash
  az boards iteration team list --team "<team>" --project "<project-name>" --organization "<org-url>" --output json
  ```
  - Look for a current iteration (date range includes today).
  - If found, suggest it as default.
  - If NOT found, show the **most recent and upcoming** iterations (not archived ones). Filter to show only iterations from the last 3 months and forward.
  - Also allow free-text entry.

**3e. Parent work item** (optional but validated)

**⚠️ Always validate the parent's type before using it.** A PBI's parent MUST be a Feature. If the user provides a parent that is not a Feature, follow the hierarchy decision table above.

- If the user provided a numeric parent ID:
  1. **Fetch and inspect** the work item type:
     ```bash
     az boards work-item show --id <id> --expand Relations --organization "<org-url>" --output json
     ```
  2. If it is a **Feature** → use it as parent. ✅
  3. If it is a **PBI** → follow the hierarchy decision table (create a Feature, re-parent, etc.).
  4. If it is an **Epic** → create a Feature under the Epic first, then use the Feature as parent.
  5. If it is a **Task** → navigate up: find the Task's PBI parent, then its Feature grandparent. Use the Feature.
  6. **Always confirm** the resolved parent with the user before proceeding.

- If the user provided keywords:
  ```bash
  az boards query --wiql "SELECT [System.Id], [System.Title], [System.WorkItemType] FROM WorkItems WHERE ([System.WorkItemType] = 'Feature' OR [System.WorkItemType] = 'Epic') AND [System.Title] CONTAINS '<keywords>'" --project "<project-name>" --organization "<org-url>" --output json
  ```
  - Present matches and ask user to confirm.

- If the user did not mention a parent: ask whether to create without a parent or search for one.
  - If creating without a parent and this is one of multiple PBIs being created → a Feature parent is strongly recommended. Propose creating one.

### 4. Confirm Before Creation

Display a summary of all collected fields:

```
## PBI Summary

- **Title**: <title>
- **Description**: <description or "none">
- **Project**: <project>
- **Area Path**: <area-path>
- **Iteration**: <iteration>
- **Parent**: <parent-id and title, or "none">

Proceed? (or tell me what to change)
```

Ask the user to confirm or edit. Keep this lightweight — a simple "yes" should suffice.

### 5. Create the Work Item(s)

Work item creation uses a **two-step process**: create with `az boards` (basic fields only), then update Description and Acceptance Criteria via the helper script to set **markdown format**.

The `az boards` CLI does not support multiline markdown fields — it truncates content at newlines and cannot set the field format to markdown. The helper script `scripts/azdo-update-fields.py` handles this via the REST API.

> ⛔ **NEVER** pass `--description` to `az boards work-item create` or `az boards work-item update`. It truncates at the first newline. Use the helper script for ALL multiline fields.
>
> ⛔ **NEVER** pass `--parent` for PBI or Feature creation. It only works for `--type Task`. Use `az boards work-item relation add` after creation.

**5a. Create a Feature (if hierarchy requires it)**

If the hierarchy decision table (Step 3e / "Starting from an Existing Work Item") determined that a Feature is needed:

```bash
az boards work-item create --title "<feature-title>" --type "Feature" --project "<project-name>" --area "<area-path>" --iteration "<iteration-path>" --organization "<org-url>" --output json
```

- Extract the Feature `id` from the output.
- Do **not** pass `--description` — set it via the helper script in step 5c.
- If the Feature should have an Epic parent, link it:
  ```bash
  az boards work-item relation add --id <feature-id> --relation-type "parent" --target-id <epic-id> --organization "<org-url>" --output json
  ```
- If an existing PBI needs to move under this Feature, re-parent it (see "Other update operations" below).

**Feature description** follows a lighter template than PBI — see `templates/feature-template.md`:
- Outcome / business value statement
- Scope summary
- Child PBI list with links
- No user story format or Given/When/Then AC — those belong on PBIs

**5b. Create the PBI (basic fields only)**
```bash
az boards work-item create --title "<title>" --type "Product Backlog Item" --project "<project-name>" --area "<area-path>" --iteration "<iteration-path>" --organization "<org-url>" --output json
```
- Do **not** pass `--description` here — it will be set via the helper script in step 5c.
- Do **not** pass `--parent` here — it will be linked in step 5d.
- Extract the work item `id` from the output.

**Error handling:**
- Permission denied → "You don't have permission to create work items under this area path. Check your account (<user>) or try a different area path."
- Invalid area/iteration → Re-prompt for that specific field, don't ask for everything again.
- Work item type not found → "This project may use a different process template (e.g., 'User Story' for Agile). Check project settings."
- Do **not** retry creation automatically to avoid duplicates.

**5c. Set Description and Acceptance Criteria as Markdown**

Write the markdown content to temporary files, then run the helper script:

```bash
# Write description and acceptance criteria to temp files
# (use Python, PowerShell, or any method that preserves UTF-8 and newlines)

python skills/_lib/azdo-update-fields.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --field "System.Description=<path-to-desc.md>" \
    --field "Microsoft.VSTS.Common.AcceptanceCriteria=<path-to-ac.md>"
```

The script:
- Authenticates automatically (PAT via `AZURE_DEVOPS_EXT_PAT`, bearer via `ADO_TOKEN`, or `az account get-access-token`)
- Sets both the field content and the field format to Markdown in one API call
- Retries on transient errors (429, 502, 503, 504) with exponential backoff
- Outputs JSON with the updated work item ID, title, URL, and confirmed field formats

**If the script fails after PBI creation (partial success):**
- Report the created work item ID to the user
- The script is idempotent — it can be safely re-run with the same work item ID
- Provide the exact command for manual retry

Clean up temporary files after successful update.

**5d. Link parent (if specified)**

> ⚠️ Remember: `--parent` only works for Task creation. For PBI and Feature, always use `relation add`.

```bash
az boards work-item relation add --id <new-pbi-id> --relation-type "parent" --target-id <parent-feature-id> --organization "<org-url>" --output json
```
- **Verify** the parent is a Feature (for PBIs) or an Epic (for Features). Do not link PBI → PBI.
- If linking fails:
  - **Do not** delete or re-create the PBI.
  - Show partial-success:
    > ⚠ PBI created (ID: <id>) but parent linking failed: <error>. Link manually: `az boards work-item relation add --id <id> --relation-type "parent" --target-id <parent-id>`

### 6. Display Result

```
## ✓ PBI Created

- **ID**: <work-item-id>
- **Title**: <title>
- **Project**: <project>
- **Area Path**: <area-path>
- **Iteration**: <iteration>
- **Parent**: <parent-id> (if linked)
- **URL**: <direct-url>
```

### 6b. Markdown Gotchas (critical)

When generating markdown content for `System.Description` or `Microsoft.VSTS.Common.AcceptanceCriteria`, follow these rules — they are non-obvious failure modes that produce broken-looking content in ADO:

1. **Content must be Markdown, never HTML.** Do not use `<b>`, `<br>`, `<ul>`, `<li>`, `<div>`, or any HTML tags. When the helper script sets the field format to Markdown, any HTML tags will render as raw escaped text (e.g., users see literal `<b>Goal:</b>` instead of **Goal:**). Use markdown: `**bold**`, `- list items`, blank lines for paragraphs, `---` for horizontal rules.
   - ❌ `<b>Goal:</b><br><ul><li>Item one</li></ul>`
   - ✅ `**Goal:**\n\n- Item one`

2. **`#NNNN` does NOT autolink in rendered markdown.** Azure DevOps autolinks `#NNNN` in plain-text comments, but in **markdown-formatted description / AC fields it does not**. Always use a full link:
   - ❌ `See #1021105 for the foundation.`
   - ✅ `See [#1021105](https://dev.azure.com/<org>/<project>/_workitems/edit/1021105) for the foundation.`
   - This applies in tables, bullet lists, and prose. Apply it to **every** work item reference, including the parent and any sibling/dependency references.

3. **Code blocks suppress markdown link rendering.** ASCII diagrams or fenced code blocks hide any `[text](url)` links inside. If you want a hierarchy or order diagram with clickable links, use a **markdown bullet tree** instead of a code block:
   - ❌ ```\n#1021105 → #1021174\n```  (links won't render)
   - ✅ Bulleted tree with explicit `[#NNNN](url)` per node

4. **Field format defaults to HTML.** When updating fields via `az boards work-item update --fields "..."` or via raw REST `PATCH` without setting `multilineFieldsFormat`, ADO renders the content as HTML — escaping markdown syntax. **Always use the helper script** (which sets format = Markdown) for any multiline field write — both on create and on update.

5. **`az boards work-item update --description "..."` truncates at the first newline.** The same limitation that applies to `create`. Never use it for multiline content. Use the helper script instead.

### 7. Save Defaults

If the `ado` block in `.dobby/config.json` is missing or differs from the values collected during this run, offer to save:

> Save these as defaults for next time? (org, project, team)

If yes, update `.dobby/config.json` so the `ado` block contains the current values. Preserve `backend` and any other top-level keys. Create the `.dobby/` directory and the file if needed (with `{ "backend": "ado", "ado": { ... } }`).

## Error Handling

- **Wrong identity**: If `az devops project list` fails after `az account show` succeeds, the user is likely logged into the wrong account. Show the current identity and suggest `az login`. Also confirm with the user that the displayed account is the one they want — `az account show` may return a stale/long-lived corporate account even when the user expects another.
- **Auth expiry mid-flow**: If any command fails with auth error after initial validation, tell the user to re-run `az login`.
- **SSL / certificate errors** (`SSL: CERTIFICATE_VERIFY_FAILED`, `self-signed certificate in certificate chain`): typical on corporate networks with TLS inspection. Preferred fix: set `REQUESTS_CA_BUNDLE`, `AZURE_CLI_CA_BUNDLE`, and `SSL_CERT_FILE` to a `cacert.pem` bundle that contains the corporate root CA. Insecure fallback: `AZURE_CLI_DISABLE_CONNECTION_VERIFICATION=1` for the current shell.
- **`'devops' is misspelled or not recognized`**: the `azure-devops` extension is not installed in the current `az` install. Run `az extension add --name azure-devops` (with the SSL workaround above if needed).
- **Network errors**: Suggest checking connectivity.
- **Never retry PBI creation automatically** — ask before retrying to prevent duplicates.
- **Partial success**: If PBI is created but parent linking fails, clearly report what succeeded and what failed with the work item ID.
- **Permission errors on create**: Show current identity and suggest checking account or area path permissions.

### Shell quoting tips

- **PowerShell + complex `--query`**: JMESPath expressions with `{ }`, `:`, and quoted field names (e.g. `--query "{id:id, type:fields.\"System.WorkItemType\"}"`) are fragile under PowerShell quoting and frequently fail with `argument --query: invalid jmespath_type value`. Prefer one of:
  - Use the simplest possible `--query` (e.g. `--query "[id]"`), or
  - Drop `--query`, use `--output json`, and parse the JSON in Python: `... --output json | python -c "import sys,json; d=json.load(sys.stdin); print(d['id'])"`.
- Always prefer piping JSON to a small Python one-liner over fighting cross-shell quoting.

## Guardrails

- Always show the logged-in identity early so the user can catch wrong-account issues before wasting time
- **Always validate parent work item type** — a PBI's parent must be a Feature, never another PBI
- **Always inspect existing items** before creating children — use `--expand Relations` to see the parent chain
- **Never use `--description`** on create or update — always use the helper script for multiline fields
- **Never use `--parent`** for PBI or Feature creation — only works for Tasks; use `relation add` instead
- **Always create PBIs as `Product Backlog Item`** — never as `Task` (unless explicitly creating a Task)
- Trust user-provided field values for area/iteration — don't validate them against listings before attempting creation
- Skip prompts for fields already provided in the request
- Batch missing-field prompts into as few interactions as possible
- Never assume team name — always discover via `az devops team list`
- Never retry creation without explicit user confirmation
- Use `--output json` on all `az` commands for reliable parsing
- Include `--organization` on all commands unless a confirmed default exists

## Updating an Existing PBI

The same helper script is used to **update** existing work items. This includes refining a description, replacing acceptance criteria, or fixing field-format issues (e.g., a PBI that was created with HTML format and needs to be re-saved as Markdown).

```bash
python skills/_lib/azdo-update-fields.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --field "System.Description=<path-to-desc.md>" \
    --field "Microsoft.VSTS.Common.AcceptanceCriteria=<path-to-ac.md>"
```

The script uses `op: add`, which is upsert-safe — it works whether the field has a current value or not.

### Other update operations

For **non-multiline fields** (title, area path, iteration, priority), `az boards work-item update --fields "Field=value"` is fine.

For **re-parenting** (moving a work item under a different parent):
```bash
az boards work-item relation remove --id <id> --relation-type parent --target-id <old-parent-id> --yes --organization "<org-url>"
az boards work-item relation add    --id <id> --relation-type parent --target-id <new-parent-id> --organization "<org-url>"
```

For **predecessor / successor** ordering between sibling PBIs:
```bash
az boards work-item relation add --id <from-id> --relation-type Successor --target-id <to-id> --organization "<org-url>"
```
(`Predecessor` is the inverse — pick one direction per pair, ADO mirrors automatically.)

After any update, re-fetch with `az boards work-item show --id <id> --output json` to confirm the change.

## When to Split into a Feature + Multiple PBIs

In this project/process, **when creating multiple related PBIs, always group them under a Feature**. Do not create PBIs under another PBI — that violates ADO hierarchy.

### Decision rules

| Scenario | Action |
|---|---|
| **1 PBI, existing Feature parent** | Create PBI under the Feature |
| **1 PBI, no Feature parent** | Create under existing Feature if one fits, or create standalone |
| **2–3 related PBIs** | Ensure a Feature parent exists; create PBIs as siblings under it |
| **>3 PBIs, or a clear multi-phase deliverable** | Create a new Feature (name: `"<Product> - <Feature Name>"`), parent all PBIs under it |
| **User references an existing PBI** | Inspect its parent chain. If no Feature exists above it, create one and re-parent the existing PBI under it |
| **Mixed scope (refine existing + add new)** | Refine the existing PBI in place, create new sibling PBIs under the same Feature; link with Predecessor/Successor where order matters |

### Execution order

Always confirm the proposed hierarchy with the user via `ask_user` before creating any work items. Show the planned structure. Once confirmed:

1. **Create the Feature** (if needed) — use the two-step process (create + helper script for markdown fields). Link to parent Epic if one exists.
2. **Re-parent existing items** if they need to move under the new Feature.
3. **Create the new PBIs** — use the two-step process for each. Link to Feature as parent.
4. **Link order** via Predecessor/Successor relations where implementation sequence matters.
5. **Cross-reference**: in each work item's description, reference siblings/dependencies as full markdown links (`[#NNNN](url)`) — see "Markdown Gotchas" section.
6. **Update the Feature description** to list all child PBIs with links and suggested implementation order.

## Usage Examples

**Full specification:**
> Create a PBI titled "Add login page" in project MyProject under feature 1234, area path "MyProject\Web", iteration "Sprint 5"

**Minimal:**
> Create a PBI "Fix header alignment"

**From an email or description:**
> Create a PBI from this: "We need to add a dark mode toggle to the settings page. Users have been requesting this for a while."

---

## Creating or Refining a Bug

Bugs follow the same two-step process as PBIs (create with `az boards`, then update multiline fields via helper script), but use **different fields and a different template**.

### Bug Fields (vs PBI)

| Field | ADO Reference | Purpose | Template section |
|---|---|---|---|
| Repro Steps | `Microsoft.VSTS.TCM.ReproSteps` | **Primary** content — summary, steps, expected/actual, root cause | First section of `bug-template.md` |
| Description | `System.Description` | **Secondary** — context, environment, related items | Second section of `bug-template.md` |
| Acceptance Criteria | `Microsoft.VSTS.Common.AcceptanceCriteria` | When is the fix verified? | Third section of `bug-template.md` |
| Severity | `Microsoft.VSTS.Common.Severity` | `1 - Critical`, `2 - High`, `3 - Medium`, `4 - Low` | Set via `az boards` `--fields` |
| Priority | `Microsoft.VSTS.Common.Priority` | 1–4 | Set via `az boards` `--fields` |

> ⚠️ For PBIs, the primary content field is `System.Description`. For Bugs, the primary content field is `Microsoft.VSTS.TCM.ReproSteps` — this is what appears prominently in the ADO Bug form.

### Bug Template

Use `templates/bug-template.md` when generating content. The template has three sections separated by HTML comments, mapping to the three multiline fields above. Key differences from the PBI template:

- No user story format (`As a… I want… so that…`)
- Repro Steps is the primary field (includes Summary, Current/Expected Behavior, Steps to Reproduce, Design Reference, Root Cause, Fix Direction)
- Description is secondary (brief context, related items)
- Acceptance Criteria focus on verifying the fix and preventing regression

### Creating a Bug

```bash
# Step 1: Create the Bug (basic fields only)
az boards work-item create \
    --title "<title>" \
    --type "Bug" \
    --project "<project-name>" \
    --area "<area-path>" \
    --iteration "<iteration-path>" \
    --organization "<org-url>" \
    --fields "Microsoft.VSTS.Common.Severity=3 - Medium" "Microsoft.VSTS.Common.Priority=2" \
    --output json

# Step 2: Set multiline fields as Markdown via helper script
python skills/_lib/azdo-update-fields.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --field "Microsoft.VSTS.TCM.ReproSteps=<path-to-repro-steps.md>" \
    --field "System.Description=<path-to-description.md>" \
    --field "Microsoft.VSTS.Common.AcceptanceCriteria=<path-to-ac.md>"
```

> ⛔ Same rules as PBIs: **NEVER** pass `--description` on `az boards` for multiline content. **NEVER** write HTML — always Markdown.

### Refining an Existing Bug

When the user asks to "refine" a bug, the workflow is:

1. **Fetch current state**: `az boards work-item show --id <id> --org "<org-url>" -o json`
2. **Extract existing content** from `Microsoft.VSTS.TCM.ReproSteps`, `System.Description`, and `Microsoft.VSTS.Common.AcceptanceCriteria`
3. **Preserve user-provided content**: screenshots (`![alt](attachment-url)`), original observations, and user-added notes must be kept — do not discard them
4. **Enrich with codebase context**: search the repo for relevant design docs, code references, and test specs to add Design Reference, Root Cause, and Fix Direction sections
5. **Generate updated markdown** following `templates/bug-template.md`
6. **Write to temp files and update** via the helper script
7. **Verify** by re-fetching the work item and confirming field lengths are non-zero

### Bug Hierarchy

Bugs follow the same ADO hierarchy rules as PBIs:

| Child type | Valid parent type |
|---|---|
| Bug | Feature (or no parent) |
| Task | Bug |

A Bug's parent must be a Feature — never another Bug or PBI. Use `az boards work-item relation add` to link (not `--parent`).

## Optional Quality Gate

After successful creation (PBI, Feature, or Bug), suggest:

> **Optional:** Run `grill-pbi` to stress-test the requirements and acceptance criteria before moving to refinement or proposal generation.

Do not invoke `grill-pbi` automatically — only suggest it. The user decides whether to grill.

### Bug Usage Examples

**Refine an existing bug:**
> Refine bug 1013609 based on the repo context

**Create a new bug:**
> Create a bug: "Instance badge is clipped on entity nodes"

**Create from a user report:**
> Create a bug from this: "When I add an entity twice to a diagram, the numbered circle is cut off — I can only see the corner"
