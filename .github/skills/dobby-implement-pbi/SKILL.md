---
name: dobby-implement-pbi
description: End-to-end lifecycle orchestrator for implementing a PBI or Bug — from branch creation through spec, implementation, evidence, PR, and closure. Adaptive checklist with resume/skip support.
metadata:
  author: dobby
  version: "1.0"
---

<!-- This file is a copy of `skills/dobby-implement-pbi/SKILL.md` — edit the source, not this copy. Regenerate with `python scripts/sync-skills.py`. -->

# Implement PBI — Full Lifecycle Orchestrator

Orchestrate the complete implementation lifecycle for a PBI, Bug, or User Story. This skill is an **adaptive checklist** — it delegates to specialized skills for each phase, supports resuming mid-lifecycle, and adapts to the change type (UI vs non-UI, bug vs feature, small vs large).

**Input**: A work item identifier — number, `AB#12345`, URL, or title/keywords.

## Lifecycle Phases

```
① Branch  →  ② Spec  →  ③ Grill  →  ④ Before Evidence
    ↓                                        ↓
⑤ Implement  →  ⑥ Verify  →  ⑦ After Evidence
    ↓                                        ↓
⑧ Commit/Push  →  ⑨ PR  →  ⑩ Close  →  ⑪ Done
```

At each major gate, check if the step is already done (resume support) and ask "continue, skip, or already done?" when appropriate.

## User Reminders

Read `.dobby/config.json` → `userReminders` and surface any warnings at the start. In particular:

> ⚠️ **Autopilot mode**: Before any interactive/grilling flow, remind the user to switch OFF autopilot mode so responses are captured properly.

## Phase 0: Detect Existing State

Before starting, check what already exists to support resume:

```
- Current branch: does it already match the PBI? (e.g., `fix/<id>-*` or `feat/<id>-*`)
- Existing worktree: does `git worktree list --porcelain` show a worktree whose branch matches the PBI ID?
- OpenSpec change: does `openspec/changes/*<id>*` already exist?
- Evidence: does `tests/e2e/evidence/*<id>*/before-*` exist?
- Uncommitted changes: `git status --short`
- Existing PR: `gh pr list --head <branch> --json number,url`
- PBI state: already Done?
```

If a matching worktree exists, report its path and suggest changing to that directory before proceeding.

Report findings and propose which phases to skip.

## Phase 1: Create Branch

**Skip if**: already on a PBI-matching branch, or a matching worktree already exists.

### Worktree mode (when `worktree.enabled` is `true` in `.dobby/config.json`)

Read and follow `skills/dobby-worktree/SKILL.md`, using the `create` sub-command with the work item ID and title as input.

After the worktree is created, instruct the user to change to the worktree directory:
```
cd <worktree-path>
```

**Note**: The remaining phases should execute from within the worktree directory, not the main worktree.

### Standard mode (default, or when `worktree.enabled` is `false` or absent)

Determine branch name from work item type:
- Bug → `fix/<id>-<title-slug>`
- PBI / User Story / Feature → `feat/<id>-<title-slug>`

```bash
git checkout main && git pull
git checkout -b <branch-name>
```

Slug: kebab-case, max 40 chars, from the work item title.

**Guard**: If the working tree is dirty, warn and ask the user to stash or commit first.

## Phase 2: Create Spec

**Skip if**: OpenSpec change for this PBI already exists.

Use the `dobby-propose-from-pbi` skill to fetch the work item and create an OpenSpec change:

> Read and follow `.github/skills/dobby-propose-from-pbi/SKILL.md`, treating the PBI identifier as input.

This produces `proposal.md`, `design.md`, `specs/`, and `tasks.md`.

## Phase 3: Grill / Refine

**Skip if**: user declines, or the change is trivially small (e.g., single-file CSS fix with obvious root cause).

Use the `grill-me` skill to stress-test the plan:

> Read and follow `.github/skills/grill-me/SKILL.md`, using the generated proposal and design as context.

Incorporate findings back into the design/tasks if needed.

## Phase 4: Classify Change & Capture Before Evidence

**4a. Classify UI vs non-UI:**

| Signal | Likely UI change |
|---|---|
| Title/description mentions: UI, UX, visual, layout, editor, diagram, highlight, icon, theme, tooltip, button, dialog, sidebar, toolbar, badge, clipped, rendering | Yes |
| Changed files in `renderer/components/`, `renderer/styles/`, image assets | Yes |
| Changes only in `main/`, `shared/types/`, config, docs, tests, backend services | No |
| Mixed or unclear | Ask the user |

**4b. Capture before evidence (UI changes only):**

If the project has Playwright E2E support:

1. Build the app: `npm run build`
2. Create/run `tests/e2e/bug-<id>-evidence.spec.ts` (or `pbi-<id>-evidence.spec.ts`)
3. Output to `tests/e2e/evidence/bug-<id>/before-*.png`

If Playwright is not available, ask the user to provide screenshots.

**Skip if**: before screenshots already exist, or this is a non-UI change.

## Phase 5: Implement

Use the `openspec-apply-change` skill if an OpenSpec change exists:

> Read and follow `.github/skills/openspec-apply-change/SKILL.md`.

For small/obvious fixes, implement directly without OpenSpec task tracking.

## Phase 6: Verify

Run the project's verification suite:

```bash
npm run typecheck
npm run lint
npm run test
```

Report results. If failures occur, determine if they are pre-existing or caused by the change.

## Phase 7: Capture After Evidence (UI changes)

**Skip if**: non-UI change.

1. Rebuild: `npm run build`
2. Run the evidence spec again (same spec from Phase 4)
3. Rename outputs: `after-*.png`
4. Compare before vs after — confirm the fix is visible

## Phase 8: Commit & Push

```bash
git add <changed-files>
git commit -m "<type>: <description> (<work-item-type> #<id>)

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git push -u origin <branch-name>
```

Commit type: `fix:` for bugs, `feat:` for features, `refactor:` / `docs:` / etc. as appropriate.

## Phase 9: Upload Evidence & Create PR

**9a. Upload evidence to ADO (if screenshots exist):**

Upload before/after screenshots as work item attachments:
```bash
python .github/skills/dobby-ado-close-pbi/scripts/azdo-upload-attachment.py \
    --work-item-id <id> --org "<org>" --project "<project>" <files...>
```

Post a markdown evidence comment using the attachment URLs:
```bash
python .github/skills/dobby-ado-close-pbi/scripts/azdo-add-comment.py \
    --work-item-id <id> --org "<org>" --project "<project>" --file <comment.md>
```

**Never use `az boards work-item update --discussion`** for markdown comments — it produces HTML-only output. Always use the `azdo-add-comment.py` script which patches `System.History` with `multilineFieldsFormat: "Markdown"`.

**9b. Create Pull Request:**

```bash
gh pr create --base main --head <branch> \
    --title "<type>: <description> (<work-item-type> #<id>)" \
    --body "<PR body with summary, evidence, verification>"
```

If `gh` is not authenticated, provide the manual URL and ask the user to create it.

**9c. Add dev links to ADO:**

Link commit, branch, and PR to the work item:
```bash
python .github/skills/dobby-ado-close-pbi/scripts/azdo-add-dev-links.py \
    --work-item-id <id> --org "<org>" --project "<project>" \
    --commit-url "<url>" --commit-comment "<subject> (<sha>)" \
    --branch-url "<url>" --branch-comment "Implementation branch" \
    --pr-url "<url>" --pr-comment "PR #<num>"
```

## Phase 10: Close Work Item

**Ask user confirmation before closing.**

Use the `dobby-close-pbi` skill:

> Read and follow `.github/skills/dobby-close-pbi/SKILL.md`.

The closing comment should already be posted (Phase 9a). The close skill will:
- Check acceptance criteria
- Set state to Done
- Handle child tasks if any

**Important**: PR creation (Phase 9b) happens BEFORE closing — do not close the PBI before the PR exists. This ensures traceability is complete before marking Done.

## Phase 11: Summary

Present the final status:

```
## ✓ Implementation Complete

- **Work Item**: #<id> — "<title>" [Done]
- **Branch**: <branch-name>
- **PR**: #<pr-num> — <pr-url>
- **Commit**: <short-sha>
- **Evidence**: N screenshots uploaded
- **Acceptance Criteria**: N/N checked
- **ADO URL**: <work-item-url>
```

## Adaptive Modes

### Fast Bugfix (small, obvious fix)
Skip: Grill (Phase 3), detailed spec (Phase 2 — create minimal tasks only)
Focus: Fix → Verify → Evidence → PR → Close

### Non-UI Change
Skip: Before/After evidence screenshots (Phases 4b, 7)
Include: Test results as evidence

### Resume / Partial
Detect existing state (Phase 0) and skip completed phases.
Example: "OpenSpec change already exists, branch already created — starting from Phase 3 (Grill)."

### Documentation Only
Skip: Build, evidence screenshots, extensive verification
Include: Typecheck if docs affect types

## Guardrails

- Always surface user reminders from `.dobby/config.json`
- Never close the PBI before the PR is created
- Never use `az boards work-item update --discussion` for markdown — use `azdo-add-comment.py`
- Upload screenshots BEFORE composing the evidence comment (need attachment URLs)
- At each major gate, confirm with the user before proceeding
- Check for existing state before each phase to support resume
- Keep commit messages conventional (`fix:`, `feat:`, etc.)
- Include `Co-authored-by: Copilot` trailer in commits
