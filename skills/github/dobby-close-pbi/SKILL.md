---
name: dobby-close-pbi
description: Closes a GitHub Issue via its Pull Request — commits visual evidence to the PR branch, embeds it in the PR description, and relies on Closes-on-merge for closure. Use for "close issue", "close pbi", "close this", "wrap up", "wrap up this ticket", "finish this issue", or "mark issue done".
metadata:
  author: dobby
  version: "1.0"
---

Close a GitHub Issue through its accompanying Pull Request, with implementation evidence committed to the PR branch and embedded in the PR description.


**Input**: An issue identifier — issue number, `#42` reference, or a full GitHub issue URL. Optionally, the user may provide a summary of what was done and/or screenshot file paths.

## Why this skill requires a PR

GitHub's native closure mechanism is "PR merge with `Closes #N`". This skill leans into that idiom rather than fighting it:

- The PR is the evidence vehicle (its description embeds screenshots).
- The PR's `Closes #<N>` directive closes the issue automatically when the PR merges.
- The skill never calls `gh issue close` directly — closure happens at merge time.

If no PR references the target issue, the skill stops and asks the user to create one first.

Excuses the model will be tempted by — and why they're wrong:

| Rationalization | Reality |
|---|---|
| "Sprint ends now — close it manually just this once" | A manually closed issue has no PR, no evidence trail. Open a minimal PR referencing the issue instead; that's faster than repairing traceability later. |
| "The PR can come later" | Closes-on-merge IS the evidence chain. Closing first destroys it, and nothing enforces that the PR ever comes. |
| "The user explicitly told me to" | Explain once, offer the compliant fast path. This skill never runs `gh issue close`. |

## Defaults

<!-- dobby:include:github-config-example -->

## Steps

### 1. Validate Prerequisites

<!-- dobby:include:github-prereqs -->

**Check git working tree**
```bash
git status --porcelain
```
- If the working tree has uncommitted changes outside `docs/evidence/issue-<N>/`, warn the user:
  > ⚠ Working tree has unrelated uncommitted changes. The closing flow will commit only the evidence files in `docs/evidence/issue-<N>/`. Continue?
- If they decline, stop without modifying anything.

### 2. Resolve Owner and Repo

Read from `.dobby/config.json` `github` block (same pattern as `dobby-create-pbi`). Prompt for missing values and persist them at the end if collected.

### 3. Find the Issue

Parse the user's input:

| Input format | Strategy |
|---|---|
| Numeric ID (e.g., `42`) | Direct fetch |
| `#42` | Strip `#`, fetch by ID |
| GitHub issue URL | Extract numeric ID from path, fetch |
| OpenSpec change name containing `issue-<N>` | Extract numeric ID, fetch |

```bash
gh issue view <N> --repo "<owner>/<repo>" --json number,title,state,body,labels,milestone,url
```

Extract: title, state, body, labels.

**If the issue is already Closed**, inform the user and ask whether to add additional closing remarks via a comment.

### 4. Find the PR that References the Issue

**This step is the gate** — if no open PR references the issue, the skill stops.

**4a. Search for PRs whose body contains `Closes #<N>`, `Fixes #<N>`, or `Resolves #<N>`:**
```bash
gh pr list --repo "<owner>/<repo>" --state open --json number,title,body,headRefName,url --limit 50
```

Filter the JSON output locally for any PR whose body matches the pattern `(Closes|Fixes|Resolves)\s+#<N>` (case-insensitive).

**4b. Also check GitHub's native linked-issue relationship** as a fallback:
```bash
gh api "repos/<owner>/<repo>/issues/<N>/timeline" --jq '[.[] | select(.event=="cross-referenced") | .source.issue | select(.pull_request) | {number: .number, title: .title, url: .html_url, state: .state}]'
```

**4c. Match handling:**
- **Zero PRs match** → stop. Report:
  > No open PR references issue #<N>. Create one with `Closes #<N>` in its body and re-run.
  >
  > To create a PR for the current branch: `gh pr create --body "Closes #<N>" --title "<title>"`
- **One PR matches** → use it.
- **Multiple PRs match** → list them with number, title, and URL. Ask the user to confirm which one is the closure vehicle.

Record: PR number, PR URL, PR branch name (`headRefName`), and the PR's current body.

### 5. Determine UI vs Non-UI Change

Use the same signals as the ADO close flow:

| Signal | Likely UI change |
|---|---|
| Title/description mentions: UI, UX, visual, layout, editor, button, tooltip, etc. | Yes |
| Changed files in renderer/components/styles paths or image assets | Yes |
| Changes only in backend / config / docs / tests | No |
| Mixed signals or unclear | Ask the user |

- **UI change** → screenshots are strongly recommended; proceed to step 6.
- **Non-UI change** → screenshots are optional; ask the user before proceeding.
- **Uncertain** → ask the user.

### 6. Gather Evidence

**6a. Auto-generate via Playwright (preferred when supported)**

If the project has a Playwright e2e setup with a working app launcher pattern:
- `playwright.config.ts` exists at the repo root
- `tests/e2e/` contains specs that launch the app

Create `tests/e2e/issue-<N>-evidence.spec.ts` modeled on an existing screenshot spec in the project. Output PNGs directly to `docs/evidence/issue-<N>/{before,after}-*.png` (one folder per issue). The directory is committed to the repo — do NOT gitignore it.

Build and run:
```bash
npm run build      # or the project's build command
npx playwright test tests/e2e/issue-<N>-evidence.spec.ts --reporter=list
```

**6b. User-supplied screenshots**

If Playwright isn't available or the user already has screenshots:
- Accept file paths from the user (one or more, mixed before/after).
- Copy them to `docs/evidence/issue-<N>/` with descriptive filenames (`before-<n>.png`, `after-<n>.png`).

**6c. Existing evidence directory**

If `docs/evidence/issue-<N>/` already contains screenshots from a prior invocation, add new ones alongside without overwriting. Use filename suffixes if needed (`before-2.png`, `after-2.png`).

### 7. Commit Evidence to the PR Branch

```bash
# Ensure we're on the PR branch
git fetch origin
git checkout <headRefName>
git pull --ff-only

# Stage and commit ONLY the evidence files
git add docs/evidence/issue-<N>/
git commit -m "docs(evidence): screenshots for issue #<N>"
```

If the commit succeeds, push:
```bash
git push origin <headRefName>
```

**Guardrails:**
- Stage only `docs/evidence/issue-<N>/` — never `git add .` or `git add -A`.
- If the working tree has unrelated uncommitted changes, the working-tree warning in step 1 already gave the user a chance to abort.
- If the user is not currently on the PR branch, switch to it (this is why the PR branch was recorded in step 4).
- Push **before** updating the PR description, so the embedded image URLs resolve immediately for reviewers.

### 8. Compose the PR Description Update

Build the updated PR description. Pattern:

1. **Preserve any user-authored content** at the top.
2. Append (or update if already present) a `### Before` section with image references for any `before-*.png` files.
3. Append (or update if already present) an `### After` section with image references for any `after-*.png` files.
4. Append (or ensure) a `### Closes` line with `Closes #<N>` if not already in the body.

Image embedding uses **relative paths from the repo root** so GitHub renders them via `raw.githubusercontent.com`:

```markdown
### Before
![Before — login screen](docs/evidence/issue-<N>/before-login.png)

### After
![After — login screen](docs/evidence/issue-<N>/after-login.png)
```

Each image gets a short descriptive caption. Multiple screenshots per section are encouraged.

### 9. Preview and Confirm

Show the user the proposed updated PR description. Allow them to edit, add notes, or cancel. If cancelled, the evidence files remain committed (that's fine — they're useful regardless) but the PR description is left unchanged.

### 10. Update the PR Description

Write the finalized description to a temp file and update the PR:
```bash
gh pr edit <pr-number> --repo "<owner>/<repo>" --body-file <path-to-body.md>
```

Clean up the temp file.

### 11. Acceptance Criteria Check (optional but recommended)

Read the original issue body. If it contains an `## Acceptance Criteria` section with `- [ ]` items, cross-reference each with the implementation evidence:

- Confirmed → mark as `- [x]`
- Cannot confirm → leave as `- [ ]` and list it for the user to verify manually

If any criteria changed status, offer to update the issue body:
```bash
gh issue edit <N> --repo "<owner>/<repo>" --body-file <path-to-updated-body.md>
```

Ask the user first — do not auto-update.

### 12. Optional Closing Comment on the Issue

Offer to post a brief comment on the issue summarizing the work and linking to the PR:

```markdown
## ✓ Implementation Summary

The work for this issue is in PR #<pr-number>: <pr-url>

**Changes:**
- <bullet from user input or commit summary>

**Evidence:** see the PR description for before/after screenshots.

This issue will close automatically when the PR merges.
```

```bash
gh issue comment <N> --repo "<owner>/<repo>" --body-file <path-to-comment.md>
```

Skip if the user declines. The comment is purely informational — closure still happens at PR merge.

<!-- dobby:include:verification-gate -->

### 13. Display Result

```
## ✓ Closing flow complete

- **Issue**: #<N> — <title>  (still open)
- **PR**:    #<pr-number> — <pr-title>
- **Evidence committed**: <count> file(s) to `docs/evidence/issue-<N>/`
- **PR description**: updated with embedded screenshots + `Closes #<N>`
- **PR URL**: <pr-url>
- **Issue URL**: <issue-url>

Issue #<N> will close automatically when the PR merges.
```

## Error Handling

- **Wrong identity**: `gh auth status` shows wrong user → suggest `gh auth switch`.
- **Issue not found**: clear message with the ID used.
- **No PR references the issue**: stop with the message shown in step 4c. Do not modify any state.
- **Branch checkout failure**: if the PR branch can't be checked out (uncommitted changes, conflicts), stop and let the user resolve before re-running.
- **Push failure**: if `git push` fails (force-protected, conflicts), surface the git error and let the user resolve.
- **Permission errors**: surface the underlying `gh` error.

## Guardrails

- Always show the logged-in GitHub identity early.
- Never call `gh issue close` directly — closure happens through the PR merge.
- Never `git add .` or `git add -A` — stage only the evidence directory.
- Never amend or force-push existing commits — only add new commits.
- Push the PR branch before updating the PR description, so embedded image URLs resolve.
- Multiple screenshots per before/after section are welcomed — encourage capturing different states.
- Use clean markdown in PR description updates — preserve user-authored content above the evidence sections.
- If the user cancels at the preview step, leave the evidence commit in place (it's a separate concern from the PR description update).

## Usage Examples

**By issue number:**
> Close issue 42

**With summary:**
> Close issue 42 — implemented dark mode toggle and added settings persistence

**From OpenSpec context:**
> Close the issue for change issue-42-add-dark-mode-toggle

**With test evidence:**
> Close issue 42, screenshots already in docs/evidence/issue-42/
