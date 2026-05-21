# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Dobby is **not an application** — there is no build, test, or lint pipeline. It is a collection of agent **skill definitions** (markdown `SKILL.md` files plus a few small Python helper scripts) that automate the work-item lifecycle (create → propose-spec → close-with-evidence) across two trackers: **Azure DevOps** (PBIs, via the `az` CLI + ADO REST API) and **GitHub** (Issues, via the `gh` CLI + GitHub API). PBI and Issue are treated as interchangeable concepts; the active tracker is determined per-project by `.dobby/config.json`.

The canonical skill sources live under `skills/` and are discoverable from both **GitHub Copilot CLI** (via `.github/skills/`) and **Claude Code** (via `.claude/skills/`). The repository's "code" is the prompts and the Python glue that the prompts call.

## Skill layout

Every skill has one canonical folder and two host-discovery copies:

| Path | Role |
|---|---|
| `skills/<name>/` | **Canonical source.** Edit only here. |
| `.github/skills/<name>/` | Copy for GitHub Copilot CLI discovery. Do not edit. |
| `.claude/skills/<name>/` | Copy for Claude Code discovery. Do not edit. |

Each host copy of a `SKILL.md` carries a notice immediately after the YAML frontmatter pointing back at the canonical source.

**Sync workflow:**

```bash
# After any edit under skills/<name>/, regenerate the host copies:
python scripts/sync-skills.py

# Verify a clean tree (exits non-zero on drift, names the drifted files):
python scripts/check-skill-sync.py
```

Run the sync **before committing** any skill edit. See [`scripts/README.md`](scripts/README.md) for details.

## Architecture (the big picture you can't get from one file)

The dobby workflow skills are organized as **dispatcher + backend** pairs. The user types intent ("close this pbi"); the dispatcher reads the project's tracker configuration and hands off to the matching backend implementation:

```
.dobby/config.json          ← project tracker config (replaces the old azdo-defaults.json)
                              { "backend": "ado" | "github" | "combined",
                                "ado": {...}, "github": {...},
                                "worktree": { "enabled": bool, "root": "..." } }
                              See scripts/README.md for the full schema.

skills/                     ← canonical source for all skills
│
├── dobby-create-pbi/             ←┐
├── dobby-close-pbi/              ← dispatchers (~50 lines each).
├── dobby-propose-from-pbi/       ←┘ Read config, hand off. Never touch a tracker themselves.
│
├── dobby-ado-create-pbi/         ←┐
├── dobby-ado-close-pbi/          ← Azure DevOps implementations.
├── dobby-ado-propose-from-pbi/   ←┘ Invoked by dispatchers when backend = "ado" or "combined".
│
├── dobby-gh-create-issue/        ←┐
├── dobby-gh-close-issue/         ← GitHub implementations.
├── dobby-gh-propose-from-issue/  ←┘ Invoked by dispatchers when backend = "github" or "combined".
│
├── dobby-worktree/                                              ← git worktree management (create/list/remove)
├── grill-me/                                                    ← interview user, stress-test a plan
└── openspec-{propose,apply-change,archive-change,explore}/      ← generic OpenSpec workflow skills

.github/skills/   ← generated copies for Copilot CLI discovery
.claude/skills/   ← generated copies for Claude Code discovery
```

How a dispatcher routes (using `dobby-close-pbi` as the example):

1. Read `.dobby/config.json`.
2. If the file is missing but legacy `.dobby/azdo-defaults.json` exists → run `scripts/migrate-dobby-config.py` to migrate.
3. If the file is missing entirely → ask the user "Azure DevOps, GitHub, or Combined?" and persist their answer.
4. If `backend` holds an unrecognized value → stop and ask the user to fix it (never guess).
5. Use the Read tool to load the matching backend SKILL.md (`dobby-ado-close-pbi` or `dobby-gh-close-issue`) and follow its instructions from the top.
6. For `"combined"` backend: work-item operations (state, comments, evidence upload) go to ADO skills; repo/PR operations (branch, commit evidence, PR) go to GitHub skills.

The backend skill collects its own connection details (org/project/team for ADO; owner/repo for GitHub) on first run and persists them into the corresponding block of `.dobby/config.json`. For `"combined"`, both blocks must be populated.

The dispatchers' user-facing names (`dobby-create-pbi`, `dobby-close-pbi`, `dobby-propose-from-pbi`) are preserved deliberately so existing muscle memory and natural-language intents continue to work.

### How dobby and openspec skills fit together

The `dobby-*` and `openspec-*` skills are **complementary**: `dobby-propose-from-pbi` (or `dobby-propose-from-issue` under the hood for GitHub) bridges the two by generating an OpenSpec change directory (`openspec/changes/<name>/`) seeded from a real work item; `openspec-apply-change` then implements the tasks; `dobby-close-pbi` (dispatcher) closes the work item when done and (optionally) archives the OpenSpec change.

### GitHub close flow is PR-shaped

`dobby-gh-close-issue` requires an **open PR** that references the target issue (`Closes #<N>`, `Fixes #<N>`, or `Resolves #<N>`). Screenshots and other evidence are committed to the PR branch under `docs/evidence/issue-<N>/` and embedded inline in the PR description. The issue closes automatically when the PR merges — the skill never calls `gh issue close` directly. This is intentional and matches GitHub's idiomatic workflow.

The ADO close flow is different: it talks to the work item directly and is PR-agnostic. Each backend follows its native idiom rather than forcing the trackers to look symmetric.

### Why the Python helpers exist (ADO side)

The `az boards` CLI has hard limitations that the ADO skills work around with several small REST-API scripts. Do not "simplify" by replacing them with `az boards` calls — they exist for specific reasons:

| Script | Reason it exists |
|---|---|
| `skills/dobby-ado-create-pbi/scripts/azdo-update-fields.py` | `az boards work-item create --description` truncates at newlines and cannot set the field format to **Markdown**. This script PATCHes `System.Description` and `Microsoft.VSTS.Common.AcceptanceCriteria` via REST and sets `multilineFieldsFormat` to `Markdown` in the same call. Idempotent — safe to re-run with the same work-item ID. Also used by `dobby-ado-close-pbi` and `dobby-ado-propose-from-pbi`. |
| `skills/dobby-ado-close-pbi/scripts/azdo-add-comment.py` | Posts large markdown comments (with embedded image URLs) to a work item's discussion thread. Reads the body from a file to avoid shell-quoting issues. |
| `skills/dobby-ado-close-pbi/scripts/azdo-upload-attachment.py` | Uploads image files as work-item attachments and returns their URLs, which then get spliced into the closing comment. |
| `skills/dobby-ado-close-pbi/scripts/azdo-add-dev-links.py` | Adds Development links (commit / branch / PR) to a work item, choosing between ArtifactLink and Hyperlink based on whether the org's ADO can reach the repo. |
| `skills/dobby-ado-close-pbi/scripts/evidence-store.py` | Local-only: stages before/after screenshots under `.dobby/evidence/<work-item-id>/{before,after}/` (gitignored — may contain sensitive data). |

All Azure DevOps scripts share the **same auth fallback chain** (`AZURE_DEVOPS_EXT_PAT` → `ADO_TOKEN` → `az account get-access-token`) and the same retry-with-backoff for HTTP 429/502/503/504. Keep that pattern when adding new ADO helper scripts.

### GitHub side has no helper scripts

The `gh` CLI is mature enough that the GitHub backend skills (`dobby-gh-*`) shell out directly without any Python intermediaries. `gh issue create --body-file`, `gh issue view --json`, `gh pr edit --body-file` all handle the operations cleanly, and GitHub's markdown rendering is native (no format-flag dance like ADO requires).

### Repo-level helper scripts

| Script | Purpose |
|---|---|
| `scripts/sync-skills.py` | Mirrors `skills/<name>/` → `.github/skills/<name>/` and `.claude/skills/<name>/`. Run after any skill edit. |
| `scripts/check-skill-sync.py` | Verifies the three trees match. Exits non-zero with the drifted files on failure. |
| `scripts/migrate-dobby-config.py` | One-time migration from `.dobby/azdo-defaults.json` to `.dobby/config.json`. Idempotent. Run manually or invoked by dispatchers when they detect the legacy file. |

### Cross-skill invariants

- **Backend selector lives in `.dobby/config.json`**: every dispatcher reads `backend` first and routes accordingly. Valid values are `"ado"`, `"github"`, or `"combined"`. The active tracker's connection block (`ado` and/or `github`) holds the per-backend details. File defaults take priority over CLI defaults (`az devops configure --list`, etc.).
- **Dispatchers never call tracker APIs**: `dobby-create-pbi`, `dobby-close-pbi`, and `dobby-propose-from-pbi` route only. All `az`, `gh`, REST-API, and helper-script calls live in backend skills (`dobby-ado-*` or `dobby-gh-*`).
- **Backend skills own their connection-detail collection**: dispatchers stop at the `backend` choice. Org/project/team (ADO) and owner/repo (GitHub) are collected by the backend skill on first run and persisted into the corresponding block of `.dobby/config.json`.
- **Combined mode**: `backend: "combined"` means ADO for work items + GitHub for repo/PRs. Dispatchers route work-item operations to ADO skills and repo/PR operations to GitHub skills. Both `ado` and `github` config blocks must be populated. Both identities (`az account show` + `gh auth status`) are verified at the start.
- **Unrecognized backend → stop, don't guess**: if `.dobby/config.json` has `backend` set to something other than `"ado"`, `"github"`, or `"combined"`, the dispatcher halts and asks the user to fix the file.
- **GitHub close requires a PR**: `dobby-gh-close-issue` refuses to proceed unless an open PR references the issue via `Closes #<N>`, `Fixes #<N>`, or `Resolves #<N>`. Closure happens at PR merge, not by `gh issue close`.
- **Two-step ADO PBI creation**: `az boards work-item create` (basic fields) → `azdo-update-fields.py` (markdown body). Never pass `--description` to `az boards work-item create`; it will truncate.
- **Identity displayed early**: every backend skill runs `az account show` or `gh auth status` before doing real work so the user can catch wrong-account issues before wasting a flow.
- **Trust user-provided field values**: skills should NOT pre-validate area paths, iterations, labels, or parent IDs against listings if the user supplied them. Attempt the operation, re-prompt only on failure.
- **Never auto-retry creation**: prevents duplicate work items / issues.
- **Markdown templates as the source of structure**: PBI body shape lives in `skills/dobby-ado-create-pbi/templates/pbi-template.md` (one file mapping to two ADO fields). GitHub issue body shape lives in `skills/dobby-gh-create-issue/templates/issue-template.md` (one file with Description + Acceptance Criteria sections, since GitHub has a single body field). Don't inline these structures inside the SKILL.md.

### Git worktree support

The `dobby-worktree` skill enables parallel PBI development by creating git worktrees — each PBI gets its own working directory while sharing the same `.git` store. This is opt-in via `.dobby/config.json`:

```json
{
  "worktree": {
    "enabled": true,
    "root": "../my-repo-worktrees"
  }
}
```

When `worktree.enabled` is `true`, `dobby-implement-pbi` Phase 1 delegates to `dobby-worktree create` instead of `git checkout -b`. Worktrees are created as sibling directories to the main repo (default root: `<repo-parent>/<repo-name>-worktrees/`). Directory names match branch names with `/` replaced by `-` (e.g., branch `feat/123-auth` → directory `feat-123-auth`).

Key behaviours:
- **Config shared, evidence isolated**: `.dobby/config.json` is tracked in git (shared across worktrees). `.dobby/evidence/` is gitignored (per-worktree isolation).
- **Post-close cleanup**: `dobby-close-pbi` offers to remove the worktree after successful closure (for all backends).
- **Standalone usage**: `dobby-worktree` works independently of `dobby-implement-pbi` — users can manage worktrees manually.

## Common operations

There is no build or test suite. The repo is operated through skill invocations — when working here you typically:

```bash
# Inspect/edit a skill — these are the "source files"
skills/<skill-name>/SKILL.md

# After editing a skill, sync host copies (Copilot CLI + Claude Code)
python scripts/sync-skills.py
python scripts/check-skill-sync.py     # verify no drift

# Smoke-test a helper script (Python 3, stdlib only — no pip install needed)
python scripts/migrate-dobby-config.py --dry-run
python skills/dobby-ado-create-pbi/scripts/azdo-update-fields.py --help
python skills/dobby-ado-close-pbi/scripts/evidence-store.py list --work-item-id <id>

# OpenSpec CLI (required for openspec-* and the dobby propose-from-* skills)
openspec list --json
openspec status --change "<name>" --json
openspec new change "<name>"
openspec instructions <artifact-id> --change "<name>" --json
```

Required prerequisites for end-to-end runs:

- **ADO-backed projects**: `az` CLI with the `azure-devops` extension (`az extension add --name azure-devops`), authenticated (`az login`).
- **GitHub-backed projects**: `gh` CLI installed and authenticated (`gh auth login`).
- **Both**: Python 3 (stdlib only); `openspec` CLI for the OpenSpec workflows.

### Migrating from azdo-defaults.json

If you're working in a project that still has the legacy `.dobby/azdo-defaults.json`, run the migration once:

```bash
python scripts/migrate-dobby-config.py --dry-run   # preview the result
python scripts/migrate-dobby-config.py             # apply
```

The script wraps the legacy content as `{ "backend": "ado", "ado": <legacy> }` and removes the legacy file. Idempotent — safe to re-run. Dispatchers will trigger the migration automatically on first invocation if they find the legacy file.

## OpenSpec workflow

`openspec/config.yaml` declares schema `spec-driven`. Active changes live under `openspec/changes/<name>/` with `proposal.md`, `design.md`, `tasks.md`, and optional delta `specs/`. The `openspec-*` skills wrap the CLI. Backend-specific propose-from skills add traceability:

| Backend | Change name format | Source line in `proposal.md` |
|---|---|---|
| Azure DevOps | `pbi-<id>-<slug>` | `> Source: Azure DevOps PBI [#<id>](<url>) — "<title>"` |
| GitHub | `issue-<id>-<slug>` | `> Source: GitHub Issue [#<id>](<url>) — "<title>"` |

Archived changes go to `openspec/changes/archive/YYYY-MM-DD-<name>/`.

## Conventions specific to this repo

- **Greenfield, no source code yet**: when asked to add functionality, check whether scaffolding exists; if not, propose a structure before generating files. There are no language/framework precedents to follow — ask before introducing any.
- **`todo.md` is a brainstorming scratchpad, not a spec**: don't treat statements there as finalized requirements. Surface ambiguities back to the user.
- **Commit trailer**: repository policy uses `Co-authored-by: Copilot` on commits.
- **`.dobby/evidence/` is gitignored** because ADO before-capture screenshots may contain sensitive data — never commit anything from that directory.
- **`docs/evidence/issue-<N>/` IS committed**: the GitHub close flow commits screenshots to the PR branch (under `docs/evidence/issue-<N>/`) so GitHub can render them inline in the PR description via `raw.githubusercontent.com`. These files survive PR merge into main. Prune periodically with a housekeeping commit if the directory grows large.
- **`--output json` / `--json` everywhere**: every `az` and `gh` invocation in skill prose uses JSON output for reliable parsing — keep that pattern when adding new commands.
