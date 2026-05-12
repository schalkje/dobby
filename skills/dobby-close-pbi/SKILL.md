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
  "team": "MyTeam",
  "devLinks": {
    "repoReachableFromAdo": true,
    "host": "github",
    "githubConnectionId": "<guid-of-boards-github-connection>",
    "adoProjectId": "<guid>",
    "adoRepoId": "<guid>"
  }
}
```

**`devLinks` (used by step 6c)** — declares whether the implementation repo is reachable from the org's ADO so the right link type is chosen automatically:

- `repoReachableFromAdo` (bool, **required**): `true` for ADO Repos in this org or company-GitHub repos that have a Boards <-> GitHub connection set up; `false` for private personal/external repos that the org's ADO cannot reach.
- `host` (`"github"` | `"ado"`): the implementation repo's host. Optional — usually inferred from the URL.
- `githubConnectionId`: the GUID of the project's Boards <-> GitHub connection. Required when `repoReachableFromAdo: true` and `host: "github"`. Find via `GET <org>/<project>/_apis/githubconnections?api-version=7.2-preview.1`.
- `adoProjectId` / `adoRepoId`: GUIDs for ADO Repos. Required when `host: "ado"`. Find via `az repos show --repository <name> --query "{p:project.id, r:id}"`.

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

**4e. Classify change type — UI or non-UI**

Determine whether this PBI involves visual/UI changes. Use these signals:

| Signal | Likely UI change |
|---|---|
| Title/description mentions: UI, UX, visual, layout, editor, diagram, highlight, icon, theme, tooltip, button, dialog, sidebar, toolbar | Yes |
| Changed files in `renderer/components/`, `renderer/styles/`, or image assets | Yes |
| Changes only in `main/`, `shared/types/`, config, docs, tests, backend services | No |
| Mixed signals or unclear | Ask the user |

**If UI change → screenshots are strongly recommended.** Proceed to step 4f.
**If non-UI change → screenshots are optional.** Skip to step 5.
**If uncertain → ask the user:** "This PBI might involve visible UI changes. Would you like to include before/after screenshots?"

**4f. Screenshot evidence** (before/after images)

Check for locally stored evidence screenshots:
```bash
python skills/dobby-close-pbi/scripts/evidence-store.py list --work-item-id <pbi-id>
```

Parse the JSON output and handle each phase:

**Before screenshots:**
- If **before** images exist: "Found N before screenshot(s) that will be included."
- If **no before** images exist AND this is a UI change: inform the user — "No before screenshots were captured. For future PBIs, capture before screenshots when starting work using: `python skills/dobby-close-pbi/scripts/evidence-store.py store --work-item-id <pbi-id> --phase before <files...>`"
- Continue without before images if unavailable — don't block closing.

**After screenshots:**
- If this is a **UI change**, actively prompt the user: "This is a UI change — would you like to capture after screenshots now? You can provide file paths to attach."
- If the app appears to be running (check for the process), mention it: "The app appears to be running — now is a good time to capture screenshots showing the feature in action."
- Accept file paths from the user. Store them:
  ```bash
  python skills/dobby-close-pbi/scripts/evidence-store.py store --work-item-id <pbi-id> --phase after <file1> <file2> ...
  ```
- The user may also provide image file paths directly without storing them first.
- Multiple screenshots are supported — each should have a short descriptive caption.

**If the user declines screenshots**, continue without them. Do not block closing.

**4g. Generate evidence screenshots via Playwright** (when the project supports it)

If the project has a Playwright e2e setup with a working "open model" pattern (look for `tests/e2e/` and a `help-screenshots.spec.ts` or similar), you can generate the evidence automatically instead of asking the user to capture them by hand. This is strongly preferred for UI changes.

**How to recognize the project supports this:**
- `playwright.config.ts` exists at the repo root
- `tests/e2e/` contains specs that use `_electron.launch(...)` or a similar app launcher
- A reference spec produces PNGs (e.g., `help-screenshots.spec.ts` in `cdmedit`)
- A demo / fixture model exists under `tests/e2e/fixtures/` so the spec can run deterministically

**Pattern (use the `cdmedit` repo as the reference):**

1. Create `tests/e2e/pbi-<id>-evidence.spec.ts` modeled on the project's screenshot spec.
2. Output screenshots to `tests/e2e/evidence/pbi-<id>/*.png` (one folder per PBI). **Add `tests/e2e/evidence/` to `.gitignore`** — once uploaded to ADO the images live as work-item attachments, so keeping them in git is duplication. They can always be regenerated by re-running the spec.
3. Set `viewport: { width: 1400, height: 900 }` (or the project default) and use `--trace=on-first-retry` to ease debugging.
4. Capture **at least one "before" screenshot** (initial state) and **one or more "after" screenshots** (each acceptance criterion demonstrated).
5. Use targeted element screenshots (`elementScreenshot('selector')`) rather than full-page when possible — they are easier to read and don't pick up irrelevant UI chrome.

**Build & run (do this every time before running the spec):**
```bash
# Make sure the production bundle is fresh — stale dist-electron will silently fail
npm run build      # or: node node_modules/electron-vite/bin/electron-vite.js build

npx playwright test tests/e2e/pbi-<id>-evidence.spec.ts --reporter=list
```

**Common pitfalls** (learned from PBI 1021103):
- **Stale `dist-electron/`** causes cryptic timeouts — always rebuild first.
- **Tree-label substring matching** picks up unintended items: use `:text-is("Client")` for exact match (avoids matching "Client Relations").
- **View/Edit mode**: in `cdmedit`, the "Edit" tab on entity pages only appears when the global view/edit toggle (top toolbar `button[title*="Edit mode"]`) is in **Edit** mode. Click it before clicking the Edit tab.
- **Avoid broken setup helpers**: if `setupWithDemiModel` (or equivalent) is failing, copy the launch+open pattern from `help-screenshots.spec.ts` directly rather than waiting for it to be fixed.
- **Permission-denied on `npx`/`npm`** in some shells: fall back to `node node_modules/playwright/cli.js test ...` and `node node_modules/electron-vite/bin/electron-vite.js build`.

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
   python skills/dobby-close-pbi/scripts/azdo-upload-attachment.py \
       --work-item-id <pbi-id> \
       --org "<org-url>" \
       --project "<project-name>" \
       --dry-run \
       <file1> <file2> ...
   ```
3. Upload and attach images to the work item:
   ```bash
   python skills/dobby-close-pbi/scripts/azdo-upload-attachment.py \
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
python skills/dobby-close-pbi/scripts/azdo-add-comment.py \
    --work-item-id <pbi-id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --file <path-to-comment.md>
```

This avoids shell quoting issues with large markdown content containing image URLs.

**The script PATCHes `System.History` with the `multilineFieldsFormat: "Markdown"` hint** (api-version 7.2-preview.3). The plain Comments REST API silently ignores `format` and stores everything as HTML — the patch-via-history approach is the only way to get markdown rendering. **Never use `PATCH /workItems/{id}/comments/{commentId}` to edit an existing comment** either — it has the same bug and will silently downgrade the format from `markdown` back to `html`. To "edit", always **delete + re-post** via the patched script:

```bash
python skills/dobby-close-pbi/scripts/azdo-delete-comment.py \
    --work-item-id <pbi-id> --comment-id <comment-id> \
    --org "<org-url>" --project "<project-name>"
```

### 6c. Add Development Links (commit / branch / PR)

Link the implementation commit and branch from the work item. The right link type depends on **whether the org's ADO can reach the repo** — read this from `.dobby/azdo-defaults.json` -> `devLinks.repoReachableFromAdo`.

| Repo location | `repoReachableFromAdo` | Link type | Where it shows |
|---|---|---|---|
| ADO Repos in same org | `true` | ArtifactLink | Development section |
| Company GitHub with Boards <-> GitHub connection | `true` | ArtifactLink | Development section |
| Private personal GitHub, external repo, anything ADO can't reach | `false` | Hyperlink | Links panel |

**Why this matters**: the API will *accept* a `vstfs:///GitHub/Commit/...` ArtifactLink even when no connection exists, but the work item form will then display "GitHub Commit link could not be read" because ADO has no way to fetch the commit metadata. **Posting an unresolvable ArtifactLink is worse than posting a Hyperlink** — don't do it. If `repoReachableFromAdo` is missing or unsure, default to Hyperlink.

If `devLinks` is missing entirely, ask the user once and write it back to `.dobby/azdo-defaults.json` so future PBIs use the right type without prompting.

**Discovery (when `repoReachableFromAdo: true`):**

- GitHub: `GET <org>/<project>/_apis/githubconnections?api-version=7.2-preview.1` — copy the `id` GUID into `devLinks.githubConnectionId`. Also check `GET <org>/_apis/serviceendpoint/endpoints?type=github` for an org-level connection.
- ADO Repos: `az repos show --repository <name> --org "<org-url>" --project "<project>" --query "{p:project.id, r:id}" -o json` — store both GUIDs in `devLinks`.

Run `azdo-add-dev-links.py` — it picks the right relation type based on the flags it receives:

```bash
python skills/dobby-close-pbi/scripts/azdo-add-dev-links.py \
    --work-item-id <pbi-id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --commit-url "<commit-url>" --commit-comment "<subject> (<short-sha>)" \
    --branch-url "<branch-url>" --branch-comment "Implementation branch" \
    [--pr-url "<pr-url>" --pr-comment "PR #<num>"] \
    [--gh-connection-id <guid>] \
    [--ado-project-id <guid> --ado-repo-id <guid>]
```

Behaviour:
- **GitHub URLs**: ArtifactLink iff `--gh-connection-id` (or `GH_BOARDS_CONNECTION_ID` env var) is supplied; otherwise Hyperlink. (GitHub branches always use Hyperlink — there's no GitHub Branch artifact-link type.)
- **ADO Repos URLs**: ArtifactLink iff both `--ado-project-id` and `--ado-repo-id` (or `ADO_PROJECT_ID` / `ADO_REPO_ID`) are supplied; otherwise Hyperlink.
- **Anything else**: Hyperlink.

Artifact-link URI formats (the script encodes these for you):
- `vstfs:///GitHub/Commit/<connection-id>%2F<sha>` — name `"GitHub Commit"`
- `vstfs:///GitHub/PullRequest/<connection-id>%2F<num>` — name `"GitHub Pull Request"`
- `vstfs:///Git/Commit/<projectId>%2f<repoId>%2f<sha>` — name `"Fixed in Commit"`
- `vstfs:///Git/Ref/<projectId>%2f<repoId>%2fGBrefs%2fheads%2f<branch>` — name `"Branch"`
- `vstfs:///Git/PullRequestId/<projectId>%2f<repoId>%2f<num>` — name `"Pull Request"`

**Always**:
1. Push the branch to origin first (otherwise the URLs 404 in browsers).
2. Use the **full 40-char SHA** in the URL — short SHAs aren't universally resolvable.
3. Run this **before** posting the closing comment so users see the links right away.

The same URLs should also appear in the `### Source` section of the closing comment for inline visibility.

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
python skills/dobby-create-pbi/scripts/azdo-update-fields.py \
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

## Usage Examples

**By PBI number:**
> Close PBI 1021108

**With summary:**
> Close PBI 1021108 — implemented language toggle tooltip and hid code fields from all views

**From OpenSpec context:**
> Close the PBI for change pbi-1021108-clarify-language-toggle-hide-code-field

**With test evidence:**
> Close PBI 1021108, all tests pass, run `npm test` for evidence
