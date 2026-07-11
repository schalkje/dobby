---
name: dobby-close-pbi
description: Closes a PBI or Bug in Azure DevOps — gathers implementation evidence, uploads screenshots, checks acceptance criteria, posts a closing summary, and sets the state to Done. Use for "close pbi", "close this pbi", "close bug", "wrap up", "wrap up this ticket", "finish this pbi", or "mark as done".
metadata:
  author: dobby
  version: "2.0"
---

Close a Product Backlog Item (PBI) in Azure DevOps with implementation evidence and a closing summary.


**Input**: A PBI identifier — work item number, `AB#12345` reference, or a full Azure DevOps work item URL. Optionally, the user may provide a summary of what was done.

## Defaults

<!-- dobby:include:ado-config-example -->

The optional `ado.devLinks` block controls how commit / branch / PR links attach to the work item — its fields and behavior are documented in step 6c.

## Steps

<!-- dobby:include:ado-command-rules -->

### 1. Validate Prerequisites

<!-- dobby:include:ado-prereqs -->

### 2. Resolve Organization and Project

Same pattern as `dobby-create-pbi` and `dobby-propose-from-pbi`:
- Load the `ado` block from `.dobby/config.json`
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

**4e. Classify change type — three categories:**

| Category | Evidence strategy | Trigger |
|---|---|---|
| **Bug fix / UI change** | Before + After screenshots | Work item is Bug, OR title/description mentions fix/change to existing UI elements |
| **New feature (UI)** | After screenshots only | Work item is PBI/Feature that adds new UI — there is no "before" to capture |
| **Non-UI change** | No screenshot evidence | Changes only in backend, types, config, docs, tests |

Use these signals:

| Signal | Category |
|---|---|
| Work item type = Bug + UI-related | Bug fix / UI change |
| Title mentions: fix, improve, update, change + UI keywords | Bug fix / UI change |
| Title mentions: add, create, new, implement + UI keywords | New feature (UI) |
| Changes only in `main/`, `shared/types/`, config, docs, tests, backend services | Non-UI |
| Mixed or unclear | Ask the user |

**If non-UI change → no screenshots needed.** Skip to step 5.
**If UI change or new feature → proceed to 4f.**

**4f. Screenshot evidence** (Playwright-first)

**Always use Playwright when the project supports it** (Playwright config exists + E2E fixtures available). This is the default — do not ask the user to take manual screenshots when Playwright is available. Read `references/evidence-gathering.md` for the full detail: how to recognize Playwright support, the descriptive-filename rules (`<phase>-NN-<description>.png`), the evidence spec pattern (output to `tests/e2e/evidence/<prefix>-<id>/`, gitignored), the build-and-run commands, and the after-evidence comment format.

**When the `dobby-implement-pbi` orchestrator invoked this skill**, before evidence should already be uploaded (Phase 4c). Check the work item discussion for an existing "Before Evidence" comment. If present, only after evidence needs to be gathered here.

**When this skill is invoked standalone** (not from the orchestrator), gather all evidence now:
- Check for existing before/after screenshots in `tests/e2e/evidence/<prefix>-<id>/`
- If none exist and this is a UI change, generate them via Playwright following `references/evidence-gathering.md`
- If Playwright is not available, ask the user to provide file paths

**If the user declines screenshots**, continue without them. Do not block closing.

After the spec passes, hand the resulting PNGs to step 6a (upload) — no need to ask the user for files.

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

### Changes implemented
- <bullet list of what was done, derived from OpenSpec change, git history, or user input>

### Source
- **Commit**: [`<short-sha>`](<commit-url>) — *<commit subject>*
- **Branch**: [`<branch-name>`](<branch-url>)
- **Repo**: [<owner>/<repo>](<repo-url>)

### Out of scope
- <anything explicitly not changed or deferred, from the PBI scope>

### Evidence
- <test results, OpenSpec change reference>

### Before
![Before — <description>](<attachment-url>)

### After
![After — <description>](<attachment-url>)

### Developer notes
- <optional free-form notes from the developer>

### Child tasks
<all closed / N open remaining>

### Acceptance criteria
<all checked / N unchecked — list any that could not be confirmed>
```

**Always include the `### Source` section.** Resolve the values from the local git repo:

```bash
# Find the implementation commit (search recent history for the PBI id)
git --no-pager log --oneline -50 --all --grep="<pbi-id>"

# If no match by id, the most recent commit on the working branch is usually the one
git --no-pager log -1 --format="%H %s"

# Get the branch + remote URL
git rev-parse --abbrev-ref HEAD
git remote get-url origin
```

Build URLs from the remote:

| Remote                                               | Commit URL                                  | Branch URL                                     |
|------------------------------------------------------|---------------------------------------------|------------------------------------------------|
| `https://github.com/<owner>/<repo>.git`              | `https://github.com/<owner>/<repo>/commit/<full-sha>` | `https://github.com/<owner>/<repo>/tree/<branch>` |
| `https://dev.azure.com/<org>/<proj>/_git/<repo>`     | `<repo-url>/commit/<full-sha>`              | `<repo-url>?version=GB<branch>`                |

**If the branch isn't pushed yet**, push it before posting (or warn the user the URLs won't resolve until they push). Use the **full 40-char SHA** in URLs — short SHAs work in GitHub but not in all hosts.

**Section rules — omit sections that don't apply:**
- Omit `### Before` if no before screenshots exist
- Omit `### After` if no after screenshots exist
- Omit `### Out of scope` if everything was addressed
- Omit `### Developer notes` if the developer has no notes to add
- Omit `### Child tasks` if the PBI has no child tasks
- Omit `### Acceptance criteria` section from the comment if all are checked (they are already visible on the work item itself)
- Include `### Acceptance criteria` only if some criteria could not be confirmed — list the unchecked items
- Use multiple image lines under Before/After when multiple screenshots exist — each with a short caption
- Never use HTML comments (`<!-- -->`) in the closing comment — use clean markdown only

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
   python skills/_lib/azdo-upload-attachment.py \
       --work-item-id <pbi-id> \
       --org "<org-url>" \
       --project "<project-name>" \
       --dry-run \
       <file1> <file2> ...
   ```
3. Upload and attach images to the work item:
   ```bash
   python skills/_lib/azdo-upload-attachment.py \
       --work-item-id <pbi-id> \
       --org "<org-url>" \
       --project "<project-name>" \
       <file1> <file2> ...
   ```
4. Parse the returned JSON to get attachment URLs.
5. Replace local file path placeholders in the comment with the actual Azure DevOps attachment URLs (you need the attachment URLs before the final comment can be posted).
6. If any upload fails, warn the user and continue with remaining images.

### 6b. Post Closing Comment

Write the finalized comment (with real image URLs) to a temporary file and post it via the REST API:

```bash
python skills/_lib/azdo-add-comment.py \
    --work-item-id <pbi-id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --file <path-to-comment.md>
```

This avoids shell quoting issues with large markdown content containing image URLs.

**Never use `az boards work-item update --discussion`** for comments that contain markdown — it produces HTML-only output that strips markdown formatting. The script instead PATCHes `System.History` with the `multilineFieldsFormat: "Markdown"` hint (api-version 7.2-preview.3); the plain Comments REST API silently ignores `format` and stores everything as HTML — the patch-via-history approach is the only way to get markdown rendering. **Never use `PATCH /workItems/{id}/comments/{commentId}` to edit an existing comment** either — it has the same bug and will silently downgrade the format from `markdown` back to `html`. To "edit", always **delete + re-post** via the patched script:

```bash
python skills/_lib/azdo-delete-comment.py \
    --work-item-id <pbi-id> --comment-id <comment-id> \
    --org "<org-url>" --project "<project-name>"
```

### 6c. Add Development Links (commit / branch / PR)

<!-- dobby:include:ado-dev-links -->

### 7. Check Off Acceptance Criteria

**This step is mandatory before closing.** Read the current `Microsoft.VSTS.Common.AcceptanceCriteria` field from the work item.

**7a. Review each criterion against implementation evidence:**
- Cross-reference each acceptance criterion with the OpenSpec tasks, git changes, and test results
- For each criterion, determine: confirmed done, cannot confirm, or not applicable

**7b. Show AC status to the user:**
Present a summary showing each criterion and its status:
```
Acceptance Criteria Status:
  ✓ [1] Given X, when Y, then Z — confirmed (implemented in EntityEditor.tsx)
  ✓ [2] Given A, when B, then C — confirmed (test: EntityEditorHighlight.test.tsx)
  ? [3] Given D, when E, then F — cannot confirm (needs manual verification)
```

**7c. Update the field:**
Change every confirmed `- [ ]` checkbox to `- [x]`. Leave unconfirmed criteria unchecked.

Use the helper script to update the field as Markdown:

```bash
python skills/_lib/azdo-update-fields.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --field "Microsoft.VSTS.Common.AcceptanceCriteria=<path-to-ac.md>"
```

If any acceptance criteria cannot be confirmed as done, leave them unchecked AND include them in the closing comment under `### Acceptance criteria`.

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
openspec archive "<change-name>"
```

<!-- dobby:include:verification-gate -->

### 9. Display Result

```
## ✓ PBI Closed

- **ID**: #<work-item-id>
- **Title**: <title>
- **State**: Done
- **Acceptance criteria**: N/N checked
- **Child tasks closed**: <count> (if any)
- **Screenshots**: N attached (if any)
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
- **For UI/visual changes, always recommend screenshots before closing.** Do not silently skip screenshots for UI work.
- **Use clean markdown in closing comments** — no HTML comments (`<!-- -->`), no inline HTML. Omit empty sections rather than including placeholder text.
- **Verify acceptance criteria against evidence** — do not blindly check all boxes. Cross-reference each criterion with implementation evidence.
- **Multiple screenshots are welcome** — encourage capturing different states/views, not just a single screenshot.

### Scope

This skill handles evidence upload, acceptance criteria, state transitions, and closing comments. It does **not** create PRs or branches — those are the responsibility of the orchestrator (`dobby-implement-pbi`).

## Usage Examples

**By PBI number:**
> Close PBI 1021108

**With summary:**
> Close PBI 1021108 — implemented language toggle tooltip and hid code fields from all views
