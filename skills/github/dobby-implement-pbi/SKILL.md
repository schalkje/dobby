---
name: dobby-implement-pbi
description: End-to-end lifecycle orchestrator for implementing a GitHub Issue — from branch creation through spec, implementation, evidence, PR, and closure. Adaptive checklist with resume/skip support.
metadata:
  author: dobby
  version: "1.0"
---

Orchestrate the complete implementation lifecycle for a GitHub Issue. This skill is an **adaptive checklist** — it delegates to specialized skills for each phase, supports resuming mid-lifecycle, and adapts to the change type (UI vs non-UI, bug vs feature, small vs large).

**Input**: An issue identifier — number, `#42`, URL, or title/keywords.

This is the **GitHub flow**: implementation lands on a branch, evidence is committed to the PR branch under `docs/evidence/issue-<N>/`, and the issue closes automatically when a PR with `Closes #<N>` merges. The skill never calls `gh issue close` directly.

## Lifecycle Phases

```
① Branch  →  ② Spec  →  ③ Grill  →  ④ Before Evidence
    ↓                                        ↓
⑤ Implement  →  ⑥ Verify  →  ⑦ After Evidence
    ↓                                        ↓
⑧ Commit/Push  →  ⑨ PR (Closes #N)  →  ⑩ Close  →  ⑪ Done
```

At each major gate, check if the step is already done (resume support) and ask "continue, skip, or already done?" when appropriate.

## User Reminders

Read `.dobby/config.json` → `userReminders` and surface any warnings at the start. In particular:

> ⚠️ **Autopilot mode**: Before any interactive/grilling flow, remind the user to switch OFF autopilot mode so responses are captured properly.

## Phase 0: Detect Existing State

Before starting, check what already exists to support resume:

```
- Current branch: does it already match the issue? (e.g., `fix/<N>-*` or `feat/<N>-*`)
- Existing worktree: does `git worktree list --porcelain` show a worktree whose branch matches the issue number?
- OpenSpec change: does `openspec/changes/*issue-<N>*` already exist?
- Evidence: does `docs/evidence/issue-<N>/before-*` exist?
- Uncommitted changes: `git status --short`
- Existing PR: `gh pr list --head <branch> --json number,url,body`
- Issue state: `gh issue view <N> --json state` — already Closed?
```

If a matching worktree exists, report its path and suggest changing to that directory before proceeding. Report findings and propose which phases to skip.

## Phase 1: Create Branch

**Skip if**: already on an issue-matching branch, or a matching worktree already exists.

Determine the branch prefix from the issue's labels:
- Has a `bug` label → `fix/<N>-<title-slug>`
- Otherwise → `feat/<N>-<title-slug>`

Slug: kebab-case, max 40 chars, from the issue title.

### Worktree mode (when `worktree.enabled` is `true` in `.dobby/config.json`)

Read and follow `dobby-worktree`'s SKILL.md, using the `create` sub-command with the issue number and title as input. Then change to the worktree directory; the remaining phases execute from there.

### Standard mode (default)

```bash
git checkout main && git pull
git checkout -b <branch-name>
```

**Guard**: If the working tree is dirty, warn and ask the user to stash or commit first.

## Phase 2: Create Spec

**Skip if**: an OpenSpec change for this issue already exists.

Use the `dobby-propose-from-pbi` skill to fetch the issue and create an OpenSpec change:

> Read and follow `dobby-propose-from-pbi`'s SKILL.md, treating the issue identifier as input.

This produces `proposal.md`, `design.md`, `specs/`, and `tasks.md` under `openspec/changes/issue-<N>-<slug>/`.

## Phase 3: Grill / Refine

**Skip if**: user declines, or the change is trivially small (e.g., single-file CSS fix with an obvious root cause).

Use the `grill-me` skill to stress-test the plan, with the generated proposal and design as context. Incorporate findings back into the design/tasks if needed.

## Phase 4: Classify Change & Capture Before Evidence

**4a. Classify UI vs non-UI** using title/description keywords (UI, layout, editor, button, tooltip, theme, …) and the changed-file footprint (renderer/components/styles + image assets ⇒ UI; backend/types/config/docs/tests ⇒ non-UI). If mixed or unclear, ask the user.

**4b. Capture before evidence (UI changes only):** if the project has Playwright E2E support, build the app, create/run `tests/e2e/issue-<N>-evidence.spec.ts`, and output to `docs/evidence/issue-<N>/before-*.png`. The `docs/evidence/issue-<N>/` directory is **committed** (so GitHub renders it inline in the PR) — do not gitignore it. If Playwright is unavailable, ask the user for screenshots.

**Skip if**: before screenshots already exist, or this is a non-UI change.

## Phase 5: Implement

Use the `openspec-apply-change` skill if an OpenSpec change exists:

> Read and follow `openspec-apply-change`'s SKILL.md.

For small/obvious fixes, implement directly without OpenSpec task tracking.

## Phase 6: Verify

Run the project's verification suite (e.g., `npm run typecheck`, `npm run lint`, `npm run test`). Report results. If failures occur, determine whether they are pre-existing or caused by the change.

## Phase 7: Capture After Evidence (UI changes)

**Skip if**: non-UI change.

Rebuild, run the same evidence spec from Phase 4, write outputs as `docs/evidence/issue-<N>/after-*.png`, and compare before vs after to confirm the fix is visible.

## Phase 8: Commit & Push

```bash
git add <changed-files>
git commit -m "<type>: <description> (#<N>)

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git push -u origin <branch-name>
```

Commit type: `fix:` for bug-labeled issues, `feat:` for features, `refactor:` / `docs:` / etc. as appropriate.

## Phase 9: Create Pull Request

**9a. Commit evidence to the PR branch (if screenshots exist):**

```bash
git add docs/evidence/issue-<N>/
git commit -m "docs(evidence): screenshots for issue #<N>"
git push origin <branch-name>
```

Stage **only** `docs/evidence/issue-<N>/` — never `git add .`. Push before creating/updating the PR so the embedded image URLs resolve via `raw.githubusercontent.com`.

**9b. Create the PR with a closing directive:**

```bash
gh pr create --base main --head <branch> \
    --title "<type>: <description> (#<N>)" \
    --body-file <path-to-pr-body.md>
```

The PR body MUST contain `Closes #<N>` (or `Fixes #<N>` / `Resolves #<N>`) so the issue closes automatically on merge. Include a summary, before/after evidence sections (embedding `docs/evidence/issue-<N>/*.png` via repo-relative paths), and the verification results. If `gh` is not authenticated, provide the manual URL and ask the user to create it.

Record the PR number and URL.

<!-- dobby:combined-seam:link-pbi-to-pr -->

## Phase 10: Close Work Item

**Ask user confirmation before finalizing.**

Use the `dobby-close-pbi` skill:

> Read and follow `dobby-close-pbi`'s SKILL.md.

For the GitHub flow, closure happens at **PR merge** — the close skill verifies the PR references the issue, commits/embeds any remaining evidence, checks acceptance criteria, and relies on `Closes #<N>`. It does **not** call `gh issue close`.

**Important**: PR creation (Phase 9) happens BEFORE closing — never close the issue before the PR exists. This keeps traceability complete.

## Phase 11: Summary

```
## ✓ Implementation Complete

- **Issue**: #<N> — "<title>" [Open until merge]
- **Branch**: <branch-name>
- **PR**: #<pr-num> — <pr-url>  (Closes #<N>)
- **Commit**: <short-sha>
- **Evidence**: N screenshots committed to docs/evidence/issue-<N>/
- **Acceptance Criteria**: N/N checked
- **Issue URL**: <issue-url>
```

## Adaptive Modes

- **Fast bugfix** (small, obvious): skip Grill (Phase 3) and the detailed spec (create minimal tasks only). Focus: Fix → Verify → Evidence → PR.
- **Non-UI change**: skip before/after screenshots (Phases 4b, 7); use test results as evidence in the PR.
- **Resume / partial**: detect existing state (Phase 0) and skip completed phases.
- **Documentation only**: skip build, screenshots, and extensive verification; include typecheck if docs affect types.

## Guardrails

- Always surface user reminders from `.dobby/config.json`.
- Never close the issue before the PR is created; closure is via `Closes #<N>` at merge, not `gh issue close`.
- Never `git add .` / `git add -A` when committing evidence — stage only `docs/evidence/issue-<N>/`.
- Never amend or force-push existing commits — only add new commits.
- At each major gate, confirm with the user before proceeding.
- Check for existing state before each phase to support resume.
- Keep commit messages conventional (`fix:`, `feat:`, etc.) and include the `Co-authored-by: Copilot` trailer.
