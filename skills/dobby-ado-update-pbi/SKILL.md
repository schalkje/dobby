---
name: dobby-ado-update-pbi
description: Internal — updates/refines a PBI, Bug, or Feature in Azure DevOps. Invoked by dobby-update-pbi after backend resolution. Do not invoke directly unless forcing the ADO backend. Updates multiline fields (Description, Acceptance Criteria, Repro Steps) via the helper script to ensure Markdown format.
metadata:
  author: dobby
  version: "1.0"
---

Update or refine an existing work item (PBI, Bug, or Feature) in Azure DevOps.

This skill is the **Azure DevOps implementation** invoked by the `dobby-update-pbi` dispatcher after it resolves `backend: "ado"` from `.dobby/config.json`. Direct invocation is supported as an escape hatch.

**Input**: The user provides a work item ID and the fields/content to update. This may come from a conversation where the agent has already analyzed a bug, refined a description, or generated acceptance criteria.

## ⛔ Critical Rules (read before every run)

1. **NEVER use `--description` on `az boards work-item update`.** It truncates at the first newline. Always use the helper script (`azdo-update-fields.py`) for multiline fields.
2. **NEVER write HTML in description, acceptance criteria, or repro steps fields.** Content must be **Markdown** — not HTML. No `<b>`, `<br>`, `<ul>`, `<li>` tags. Use markdown syntax: `**bold**`, line breaks, `- list items`. The helper script sets the field format to Markdown; HTML content in a Markdown-formatted field renders as raw escaped tags.
3. **Follow the template** when generating content. PBIs use `skills/dobby-ado-create-pbi/templates/pbi-template.md`; Bugs use `skills/dobby-ado-create-pbi/templates/bug-template.md`. When updating a single section, preserve existing content in other sections unless the user explicitly asks to replace everything.
4. **Always use the helper script for multiline fields** — `az boards` cannot set markdown format.

## Field Mapping by Work Item Type

| Work Item Type | Primary content field | Other multiline fields |
|---|---|---|
| **Product Backlog Item** | `System.Description` | `Microsoft.VSTS.Common.AcceptanceCriteria` |
| **Bug** | `Microsoft.VSTS.TCM.ReproSteps` | `System.Description`, `Microsoft.VSTS.Common.AcceptanceCriteria` |
| **Feature** | `System.Description` | `Microsoft.VSTS.Common.AcceptanceCriteria` |

## Steps

### 1. Validate Prerequisites

Run these checks (same as create skill):

**1a. Check Azure CLI and extension**
```bash
az version --output json
```
- If `az` is not found → stop: "Azure CLI is not installed."
- If `azure-devops` is not listed under `extensions` → install it: `az extension add --name azure-devops`

**1b. Check Python availability**
```bash
python --version
```
- If `python` is not found → stop: "Python 3 is required for the markdown field helper script."

**1c. Check authentication**
```bash
az account show --query "{user:user.name, tenant:tenantId}" --output json
```
- If this fails → stop: "Run: `az login`"

### 2. Load Configuration

Read `.dobby/config.json` to get `organization` and `project`.

### 3. Fetch Current Work Item

```bash
az boards work-item show --id <work-item-id> --organization "<org-url>" --output json
```

Extract:
- **Type**: `fields["System.WorkItemType"]` — determines which fields and template to use
- **Title**: `fields["System.Title"]`
- **Current field values** — so you can preserve content the user didn't ask to change

Display current title and type to the user for confirmation.

### 4. Determine What to Update

Based on the user's request, determine which fields need updating:

**Simple fields** (title, area path, iteration, priority, state):
- Use `az boards work-item update --fields "Field=value"` directly.

**Multiline fields** (Description, Acceptance Criteria, Repro Steps):
- Must use the helper script (step 5).
- When updating a subset of the content (e.g., "add acceptance criteria"), fetch current content and merge intelligently — don't overwrite content the user didn't mention.

### 5. Update Multiline Fields via Helper Script

Write the markdown content to temporary files, then run the helper script:

```bash
python skills/dobby-ado-create-pbi/scripts/azdo-update-fields.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --field "System.Description=<path-to-desc.md>" \
    --field "Microsoft.VSTS.Common.AcceptanceCriteria=<path-to-ac.md>"
```

For **Bugs**, use the appropriate field for the primary content:
```bash
python skills/dobby-ado-create-pbi/scripts/azdo-update-fields.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --field "Microsoft.VSTS.TCM.ReproSteps=<path-to-reprosteps.md>" \
    --field "Microsoft.VSTS.Common.AcceptanceCriteria=<path-to-ac.md>"
```

The script:
- Authenticates automatically (PAT via `AZURE_DEVOPS_EXT_PAT`, bearer via `ADO_TOKEN`, or `az account get-access-token`)
- Sets both the field content and the field format to Markdown in one API call
- Is idempotent — safe to re-run on failure
- Uses `op: add` (upsert-safe)

**Clean up temporary files after successful update.**

### 6. Update Simple Fields (if any)

```bash
az boards work-item update --id <work-item-id> \
    --fields "System.Title=<new-title>" \
    --organization "<org-url>" \
    --output json
```

### 7. Verify the Update

```bash
az boards work-item show --id <work-item-id> --organization "<org-url>" --output json
```

Confirm the updated fields have the expected content. Report the work item URL to the user.

### 8. Add Comment (optional)

If the update includes context that should be preserved as a comment (e.g., analysis notes, screenshots, evidence), add it:

```bash
az boards work-item update --id <work-item-id> \
    --discussion "<comment-text>" \
    --organization "<org-url>" \
    --output json
```

Note: `--discussion` is fine for comments — they are plain text/markdown and don't have the truncation issue.

## Content Guidelines

- **All content must be Markdown — never HTML.** No exceptions.
- Use the template from `skills/dobby-ado-create-pbi/templates/` as the structural guide.
- When partially updating (e.g., only acceptance criteria), don't touch other fields.
- When replacing a field entirely, follow the template structure for that field.
- When the existing content is in HTML format (legacy), convert it to Markdown during the update — this fixes the format going forward.

## Error Handling

- If the helper script fails → report the error and provide the manual retry command.
- If the work item doesn't exist → stop and report.
- If the user doesn't have permissions → stop and suggest checking access.

## Efficiency Notes

- Skip prerequisite checks if they were already validated in the same session (e.g., during a create-then-update flow).
- Batch all field updates into a single helper script call when possible.
- Don't prompt for fields the user already provided.
