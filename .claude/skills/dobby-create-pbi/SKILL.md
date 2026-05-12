---
name: dobby-create-pbi
description: Create a Product Backlog Item in Azure DevOps. Collects fields interactively, validates prerequisites, and creates the work item via the az boards CLI.
metadata:
  author: dobby
  version: "1.6"
---

<!-- This file is a copy of `skills/dobby-create-pbi/SKILL.md` — edit the source, not this copy. Regenerate with `python scripts/sync-skills.py`. -->

Create a Product Backlog Item (PBI) in Azure DevOps from a conversational request.

**Input**: The user may provide any combination of: title, description, project, area path, iteration, parent work item (ID or keywords). Any missing required fields are collected interactively.

## Defaults

Check for a defaults file at `.dobby/azdo-defaults.json` in the repository root. If it exists, load defaults from it:

```json
{
  "organization": "https://dev.azure.com/myorg/",
  "project": "MyProject",
  "team": "MyTeam"
}
```

These defaults eliminate repeated prompts. If the file does not exist, defaults will be collected during the first run and the file will be created at the end (step 7).

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
- Read `.dobby/azdo-defaults.json` if it exists.
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

Generate content following the template in `skills/dobby-create-pbi/templates/pbi-template.md`. The template defines two Azure DevOps fields, both stored as **Markdown**:

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

**3e. Parent work item** (optional)
- If the user provided a numeric parent ID, use it directly.
- If the user provided keywords:
  ```bash
  az boards query --wiql "SELECT [System.Id], [System.Title], [System.WorkItemType] FROM WorkItems WHERE ([System.WorkItemType] = 'Feature' OR [System.WorkItemType] = 'Epic') AND [System.Title] CONTAINS '<keywords>'" --project "<project-name>" --organization "<org-url>" --output json
  ```
  - Present matches and ask user to confirm.
- If the user did not mention a parent: ask whether to create without a parent or search for one.

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

### 5. Create the PBI

PBI creation uses a **two-step process**: create with `az boards`, then update Description and Acceptance Criteria via the helper script to set **markdown format**.

The `az boards` CLI does not support multiline markdown fields — it truncates content at newlines and cannot set the field format to markdown. The helper script `scripts/azdo-update-fields.py` handles this via the REST API.

**5a. Create the work item (basic fields only)**
```bash
az boards work-item create --title "<title>" --type "Product Backlog Item" --project "<project-name>" --area "<area-path>" --iteration "<iteration-path>" --organization "<org-url>" --query "[id]" --output table
```
- Do **not** pass `--description` here — it will be set via the helper script in step 5b.
- Extract the work item `id` from the output.

**Error handling:**
- Permission denied → "You don't have permission to create work items under this area path. Check your account (<user>) or try a different area path."
- Invalid area/iteration → Re-prompt for that specific field, don't ask for everything again.
- Work item type not found → "This project may use a different process template (e.g., 'User Story' for Agile). Check project settings."
- Do **not** retry creation automatically to avoid duplicates.

**5b. Set Description and Acceptance Criteria as Markdown**

Write the markdown content to temporary files, then run the helper script:

```bash
# Write description and acceptance criteria to temp files
# (use Python, PowerShell, or any method that preserves UTF-8 and newlines)

python skills/dobby-create-pbi/scripts/azdo-update-fields.py \
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

**5c. Link parent (if specified)**
```bash
az boards work-item relation add --id <new-pbi-id> --relation-type "parent" --target-id <parent-id> --organization "<org-url>" --output json
```
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

1. **`#NNNN` does NOT autolink in rendered markdown.** Azure DevOps autolinks `#NNNN` in plain-text comments, but in **markdown-formatted description / AC fields it does not**. Always use a full link:
   - ❌ `See #1021105 for the foundation.`
   - ✅ `See [#1021105](https://dev.azure.com/<org>/<project>/_workitems/edit/1021105) for the foundation.`
   - This applies in tables, bullet lists, and prose. Apply it to **every** work item reference, including the parent and any sibling/dependency references.

2. **Code blocks suppress markdown link rendering.** ASCII diagrams or fenced code blocks hide any `[text](url)` links inside. If you want a hierarchy or order diagram with clickable links, use a **markdown bullet tree** instead of a code block:
   - ❌ ```\n#1021105 → #1021174\n```  (links won't render)
   - ✅ Bulleted tree with explicit `[#NNNN](url)` per node

3. **Field format defaults to HTML.** When updating fields via `az boards work-item update --fields "..."` or via raw REST `PATCH` without setting `multilineFieldsFormat`, ADO renders the content as HTML — escaping markdown syntax. **Always use the helper script** (which sets format = Markdown) for any multiline field write — both on create and on update.

4. **`az boards work-item update --description "..."` truncates at the first newline.** The same limitation that applies to `create`. Never use it for multiline content. Use the helper script instead.

### 7. Save Defaults

If `.dobby/azdo-defaults.json` does not exist, or if org/project/team differ from stored values, offer to save:

> Save these as defaults for next time? (org, project, team)

If yes, write/update `.dobby/azdo-defaults.json`. Create the `.dobby/` directory if needed.

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
- Trust user-provided field values — don't validate them against listings before attempting creation
- Skip prompts for fields already provided in the request
- Batch missing-field prompts into as few interactions as possible
- Never assume team name — always discover via `az devops team list`
- Never retry creation without explicit user confirmation
- Use `--output json` on all `az` commands for reliable parsing
- Include `--organization` on all commands unless a confirmed default exists

## Updating an Existing PBI

The same helper script is used to **update** existing work items. This includes refining a description, replacing acceptance criteria, or fixing field-format issues (e.g., a PBI that was created with HTML format and needs to be re-saved as Markdown).

```bash
python skills/dobby-create-pbi/scripts/azdo-update-fields.py \
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

If the user's request expands beyond what one PBI can reasonably hold, consider proposing a split. Heuristics:

- **1–3 child items**: stay flat — create the PBIs as siblings under the existing parent.
- **>3 child items, or a clear multi-phase deliverable**: propose a **new sub-Feature** (parented to the existing parent feature) containing the PBIs. Naming convention used in this repo: `"<Project> - <Feature Name>"` (e.g., `"CDM Editor - Tabbed Workspace"`).
- **Mixed scope (some clarification of an existing PBI + new follow-ups)**: refine the existing PBI in place AND create new sibling PBIs for follow-ups; link with Predecessor/Successor where order matters.

Always confirm the proposed split with the user via `ask_user` before creating any work items. Show the proposed hierarchy and dependency order. Once confirmed:

1. Create the Feature (if needed) and link to its parent.
2. Update the existing PBI (if its scope is being refined) — use the helper script for any markdown content.
3. Create the new PBIs — use the helper script for description and AC.
4. Link order via Predecessor/Successor relations.
5. In each work item's description, reference siblings/dependencies as full markdown links (`[#NNNN](url)`) — see "Markdown Gotchas" section.

## Usage Examples

**Full specification:**
> Create a PBI titled "Add login page" in project MyProject under feature 1234, area path "MyProject\Web", iteration "Sprint 5"

**Minimal:**
> Create a PBI "Fix header alignment"

**From an email or description:**
> Create a PBI from this: "We need to add a dark mode toggle to the settings page. Users have been requesting this for a while."
