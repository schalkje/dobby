---
name: dobby-create-pbi
description: Create a Product Backlog Item in Azure DevOps. Collects fields interactively, validates prerequisites, and creates the work item via the az boards CLI.
metadata:
  author: dobby
  version: "1.1"
---

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
- If `azure-devops` extension is not in the output → stop: "Run: `az extension add --name azure-devops`"

**1b. Check authentication and show identity**
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

**3b. Description** (optional)
- If not provided, ask if they want to add one. If they decline, skip it.

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

**5a. Create the work item**
```bash
az boards work-item create --title "<title>" --type "Product Backlog Item" --project "<project-name>" --area "<area-path>" --iteration "<iteration-path>" --description "<description>" --organization "<org-url>" --output json
```

**Error handling:**
- Permission denied → "You don't have permission to create work items under this area path. Check your account (<user>) or try a different area path."
- Invalid area/iteration → Re-prompt for that specific field, don't ask for everything again.
- Work item type not found → "This project may use a different process template (e.g., 'User Story' for Agile). Check project settings."
- Do **not** retry creation automatically to avoid duplicates.

**5b. Parse the result**
- Extract: `id`, `fields["System.Title"]`, construct URL as `<org-url>/<project>/_workitems/edit/<id>`.

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

### 7. Save Defaults

If `.dobby/azdo-defaults.json` does not exist, or if org/project/team differ from stored values, offer to save:

> Save these as defaults for next time? (org, project, team)

If yes, write/update `.dobby/azdo-defaults.json`. Create the `.dobby/` directory if needed.

## Error Handling

- **Wrong identity**: If `az devops project list` fails after `az account show` succeeds, the user is likely logged into the wrong account. Show the current identity and suggest `az login`.
- **Auth expiry mid-flow**: If any command fails with auth error after initial validation, tell the user to re-run `az login`.
- **Network errors**: Suggest checking connectivity.
- **Never retry PBI creation automatically** — ask before retrying to prevent duplicates.
- **Partial success**: If PBI is created but parent linking fails, clearly report what succeeded and what failed with the work item ID.
- **Permission errors on create**: Show current identity and suggest checking account or area path permissions.

## Guardrails

- Always show the logged-in identity early so the user can catch wrong-account issues before wasting time
- Trust user-provided field values — don't validate them against listings before attempting creation
- Skip prompts for fields already provided in the request
- Batch missing-field prompts into as few interactions as possible
- Never assume team name — always discover via `az devops team list`
- Never retry creation without explicit user confirmation
- Use `--output json` on all `az` commands for reliable parsing
- Include `--organization` on all commands unless a confirmed default exists

## Usage Examples

**Full specification:**
> Create a PBI titled "Add login page" in project MyProject under feature 1234, area path "MyProject\Web", iteration "Sprint 5"

**Minimal:**
> Create a PBI "Fix header alignment"

**From an email or description:**
> Create a PBI from this: "We need to add a dark mode toggle to the settings page. Users have been requesting this for a while."
