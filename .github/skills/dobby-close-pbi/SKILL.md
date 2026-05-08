---
name: dobby-close-pbi
description: Close a Product Backlog Item in Azure DevOps. Gathers implementation evidence, adds a closing comment, sets state to Done, and optionally closes child tasks.
metadata:
  author: dobby
  version: "1.0"
---

Close a Product Backlog Item (PBI) in Azure DevOps with implementation evidence and a closing summary.

**Input**: A PBI identifier — work item number, `AB#12345` reference, or a full Azure DevOps work item URL. Optionally, the user may provide a summary of what was done.

## Defaults

Check for a defaults file at `.dobby/azdo-defaults.json` in the repository root. If it exists, load defaults from it:

```json
{
  "organization": "https://dev.azure.com/myorg/",
  "project": "MyProject",
  "team": "MyTeam"
}
```

## Steps

### 1. Validate Prerequisites

Run these checks in parallel where possible.

**1a. Check Azure CLI and DevOps extension**
```bash
az version --output json
```
- If `az` is not found → stop: "Azure CLI is not installed."
- If `azure-devops` extension is not in the output → stop: "Run: `az extension add --name azure-devops`"

**1b. Check authentication**
```bash
az account show --query "{user:user.name, tenant:tenantId}" --output json
```
- If this fails → stop: "Run: `az login`"
- Display the logged-in user.

### 2. Resolve Organization and Project

Same pattern as `dobby-create-pbi` and `dobby-propose-from-pbi`:
- Load `.dobby/azdo-defaults.json`
- Validate Azure DevOps access
- Resolve project

### 3. Find the PBI

Parse the user's input:

| Input format | Strategy |
|---|---|
| Numeric ID (e.g., `12345`) | Direct fetch |
| `AB#12345` | Extract numeric ID, direct fetch |
| Azure DevOps URL | Extract numeric ID, direct fetch |
| OpenSpec change name containing `pbi-<id>` | Extract numeric ID, direct fetch |

```bash
az boards work-item show --id <id> --organization "<org-url>" --output json
```

Extract: title, state, type, description summary, acceptance criteria, child tasks, related links.

**If the PBI is already Done/Closed**, inform the user and ask if they want to add additional closing remarks.

### 4. Gather Implementation Evidence

Collect evidence from multiple sources automatically. Each source is optional — use whatever is available.

**4a. OpenSpec change** (if present)

Look for an OpenSpec change linked to this PBI:
- Check for a change directory matching `pbi-<id>-*` in `openspec/changes/`
- If found, read `proposal.md` for what was planned and `tasks.md` for task completion status
- Report which tasks are done vs pending

**4b. Git history** (if in a git repository)

Look for recent commits referencing this PBI:
```bash
git --no-pager log --oneline --since="2 weeks ago" --all --grep="<pbi-id>" 2>/dev/null
git --no-pager log --oneline --since="2 weeks ago" --all --grep="AB#<pbi-id>" 2>/dev/null
```

Also check for recent commits on the current branch that may be related (by looking at changed files that match the PBI scope).

**4c. Test results** (if available)

If the user provides test evidence or if test commands are available:
- Run tests if the user asks for it
- Include pass/fail summary
- Note: do NOT run tests automatically without user confirmation

**4d. User-provided summary**

If the user included a summary of what was done, use it as the primary evidence.

**4e. Screenshot evidence** (before/after images)

Check for locally stored evidence screenshots:
```bash
python .github/skills/dobby-close-pbi/scripts/evidence-store.py list --work-item-id <pbi-id>
```

Parse the JSON output:
- If **before** images exist, inform the user: "Found N before screenshot(s) that will be included."
- If **no before** images exist, display an informational note: "No before screenshots were captured. Continuing without before images."
- Ask the user if they want to attach **after** screenshot files. If yes, collect file paths and store them:
  ```bash
  python .github/skills/dobby-close-pbi/scripts/evidence-store.py store --work-item-id <pbi-id> --phase after <file1> <file2> ...
  ```
- The user may also provide after screenshots as file paths directly without storing them first.

**Note**: Before screenshots are captured *before* work begins, using:
```bash
python .github/skills/dobby-close-pbi/scripts/evidence-store.py store --work-item-id <pbi-id> --phase before <file1> <file2> ...
```
Remind the user of this capability if no before images are found.

### 5. Gather Child Tasks

```bash
az boards query --wiql "SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType] FROM WorkItemLinks WHERE ([Source].[System.Id] = <pbi-id>) AND ([System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward') AND ([Target].[System.WorkItemType] = 'Task') MODE (MustContain)" --project "<project-name>" --organization "<org-url>" --output json
```

If child tasks exist:
- List them with their current state
- Ask if the user wants to close open tasks along with the PBI
- If yes, close each task:
  ```bash
  az boards work-item update --id <task-id> --state "Done" --organization "<org-url>" --output yaml
  ```

### 6. Compose and Confirm Closing Comment

Build a closing comment for the PBI Discussion field. Use this structure:

```markdown
## ✓ Completed — Implementation Summary

**Changes implemented:**
- <bullet list of what was done, derived from OpenSpec change, git history, or user input>

**What is preserved / out of scope:**
- <anything explicitly not changed, from the PBI scope>

**Evidence:**
- <git commits, test results, OpenSpec change reference>

### Before
<!-- Include this section only if before screenshots exist -->
![Before — <description>](<attachment-url>)

### After
<!-- Include this section only if after screenshots exist -->
![After — <description>](<attachment-url>)

**Developer notes:**
- <optional free-form notes from the developer>

**Child tasks:** <all closed / N open remaining>
```

**Composing the comment:**

1. Fill in text sections from gathered evidence (steps 4a–4d).
2. For image sections, use **local file paths as placeholders** (e.g., `![Before](local:screenshot.png)`).
3. Present the comment preview to the user for confirmation — **do NOT upload images yet**.
4. Allow the user to edit, add notes, or cancel at this point.
5. If cancelled, abort — do not change work item state or post anything.

### 6a. Upload Images and Finalize Comment

After the user confirms the closing comment:

1. Collect all image file paths (before + after screenshots).
2. Validate files before uploading:
   ```bash
   python .github/skills/dobby-close-pbi/scripts/azdo-upload-attachment.py \
       --work-item-id <pbi-id> \
       --org "<org-url>" \
       --project "<project-name>" \
       --dry-run \
       <file1> <file2> ...
   ```
3. Upload and attach images to the work item:
   ```bash
   python .github/skills/dobby-close-pbi/scripts/azdo-upload-attachment.py \
       --work-item-id <pbi-id> \
       --org "<org-url>" \
       --project "<project-name>" \
       <file1> <file2> ...
   ```
4. Parse the returned JSON to get attachment URLs.
5. Replace local file path placeholders in the comment with the actual Azure DevOps attachment URLs.
6. If any upload fails, warn the user and continue with remaining images.

### 6b. Post Closing Comment

Write the finalized comment (with real image URLs) to a temporary file and post it via the REST API:

```bash
python .github/skills/dobby-close-pbi/scripts/azdo-add-comment.py \
    --work-item-id <pbi-id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --file <path-to-comment.md>
```

This avoids shell quoting issues with large markdown content containing image URLs.

### 7. Check Off Acceptance Criteria

Before closing, mark all acceptance criteria as completed. Read the current `Microsoft.VSTS.Common.AcceptanceCriteria` field and change every `- [ ]` checkbox to `- [x]`.

Use the helper script to update the field as Markdown:

```bash
python .github/skills/dobby-create-pbi/scripts/azdo-update-fields.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --field "Microsoft.VSTS.Common.AcceptanceCriteria=<path-to-ac.md>"
```

If any acceptance criteria cannot be confirmed as done, leave them unchecked and flag them in the closing comment.

### 8. Close the PBI

**8a. Add closing comment**

The closing comment was already posted in step 6b using the REST API with image URLs. If step 6b was skipped (no images), fall back to:
```bash
az boards work-item update --id <pbi-id> --discussion "<closing-comment>" --organization "<org-url>" --output json
```

**8b. Set state to Done**
```bash
az boards work-item update --id <pbi-id> --state "Done" --organization "<org-url>" --output json
```

**Error handling:**
- If the state transition fails (e.g., workflow rules require intermediate states like "Committed" → "Done"), try the required intermediate state first.
- If closing fails due to required fields, report which fields are missing and ask the user.
- If the PBI has open child tasks and the project rules prevent closing parents with open children, inform the user and offer to close children first.

**8c. Archive OpenSpec change** (optional)

If an OpenSpec change was found in step 4a, offer to archive it:
```bash
openspec archive --change "<change-name>"
```

### 9. Display Result

```
## ✓ PBI Closed

- **ID**: #<work-item-id>
- **Title**: <title>
- **State**: Done
- **Child tasks closed**: <count> (if any)
- **Closing comment**: added to Discussion
- **URL**: <direct-url>
```

## Error Handling

- **Wrong identity**: Show current identity and suggest `az login`.
- **PBI not found**: Clear message with the ID used.
- **State transition failure**: Report allowed transitions and suggest next steps.
- **Child task closure failure**: Report which tasks failed and continue with the PBI.
- **Partial success**: If PBI is closed but child tasks or comment failed, report what succeeded.
- **Permission errors**: Show current identity and suggest checking permissions.

## Guardrails

- Always show the logged-in identity early.
- Show the closing comment to the user before posting it.
- Do not close child tasks without user confirmation.
- Do not run tests automatically — only if the user asks.
- Use `--output json` on all `az` commands for reliable parsing.
- Include `--organization` on all commands unless a confirmed default exists.
- If the PBI is already Done, don't fail — offer to add remarks.

## Usage Examples

**By PBI number:**
> Close PBI 1021108

**With summary:**
> Close PBI 1021108 — implemented language toggle tooltip and hid code fields from all views

**From OpenSpec context:**
> Close the PBI for change pbi-1021108-clarify-language-toggle-hide-code-field

**With test evidence:**
> Close PBI 1021108, all tests pass, run `npm test` for evidence
