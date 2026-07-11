# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Dobby is **not an application** — there is no build, test, or lint pipeline. It is a collection of agent **skill definitions** (markdown `SKILL.md` files plus a few small Python helper scripts) that automate the work-item lifecycle (create → propose-spec → close-with-evidence) across two trackers: **Azure DevOps** (PBIs, via the `az` CLI + ADO REST API) and **GitHub** (Issues, via the `gh` CLI + GitHub API). PBI and Issue are treated as interchangeable concepts; each project consumes a flat, scenario-specialized skill set assembled at build time (the scenario is recorded in `.dobby/config.json`), rather than a runtime dispatcher choosing a backend.

The canonical skill sources live under `skills/` and are discoverable from both **GitHub Copilot CLI** (via `.github/skills/`) and **Claude Code** (via `.claude/skills/`). The repository's "code" is the prompts and the Python glue that the prompts call.

## Skill layout

Skills are **assembled per scenario at build time**, not routed at runtime. Sources live in three tiers under `skills/`; a generator emits a flat, scenario-specialized skill set into the host-discovery directories.

| Path | Role |
|---|---|
| `skills/_lib/` | Shared helper scripts (`azdo-*.py`). Authored once; bundled into a scenario only when used. |
| `skills/_common/` | Scenario-independent, dobby-authored skills (`grill-*`, `dobby-worktree`). Copied into every scenario. |
| `skills/ado/`, `skills/github/`, `skills/combined/` | Scenario-specialized prose, under the user-facing names. |
| `skills/manifest.json` | Assembly contract: per scenario, which source + `_lib` scripts make each skill. |
| `.github/skills/<name>/`, `.claude/skills/<name>/` | **Generated** copies (dobby's own = the github scenario). Do not edit — edit the source tier and regenerate. |

Each generated `SKILL.md` carries a notice after the YAML frontmatter pointing back at its scenario source.

**Generate workflow:**

```bash
# After any edit under skills/, regenerate dobby's own host copies (github scenario):
python scripts/build-skills.py dev

# Verify a clean tree (exits non-zero on drift, names the drifted files):
python scripts/check-skill-sync.py
```

On Windows/PowerShell, `dobby.ps1` in the repo root wraps these (`.\dobby.ps1 dev`, `.\dobby.ps1 check`, `.\dobby.ps1 build`, `.\dobby.ps1 init`).

Run `dev` **before committing** any skill-source edit. See [`scripts/README.md`](scripts/README.md) for the manifest schema and the `build` / `init` modes.

## Architecture (the big picture you can't get from one file)

A project targets exactly one scenario, so dobby specializes the skills for it **at generation time** rather than routing at every invocation. The generator (`scripts/build-skills.py`) assembles a **flat** skill set under the user-facing names (`dobby-create-pbi`, `dobby-update-pbi`, `dobby-propose-from-pbi`, `dobby-close-pbi`, `dobby-implement-pbi`) — no dispatcher, no nested backend `SKILL.md` reads, no `backend`-key branching at invocation.

```
.dobby/config.json          ← per-project connection details + the recorded scenario
                              { "backend": "ado" | "github" | "combined",  // a RECORD, not a runtime router
                                "ado": {...}, "github": {...},
                                "worktree": { "enabled": bool, "root": "..." } }

skills/                     ← three tiers of source
├── _lib/        azdo-update-fields.py, azdo-add-comment.py, azdo-add-dev-links.py,
│                azdo-upload-attachment.py, azdo-delete-comment.py, azdo-get-comments.py
│                                                        ← shared, bundled once per scenario when used
├── _common/     grill-*, dobby-worktree                 ← copied into every scenario
│                (openspec-* are NOT bundled — installed per-project via `openspec init`)
├── ado/         dobby-{create,update,propose,close,implement}-pbi   ← ADO-specialized prose
├── github/      dobby-{create,update,propose,close,implement}-pbi   ← GitHub-specialized prose
├── combined/    dobby-close-pbi  +  _fragments/link-pbi-to-pr.md    ← only what genuinely spans both
└── manifest.json

scripts/build-skills.py     ← assembler. Modes: build (all → build/<scenario>/),
                              init (<target> <scenario>), dev (github → dobby's own .claude + .github)
build/                      ← gitignored inspection artifact
.github/skills/, .claude/skills/  ← generated copies (dobby itself = the github scenario)
```

How the generator assembles a scenario (using `combined` as the interesting case):

1. Read `skills/manifest.json`.
2. Copy every `_common` skill into the scenario.
3. For each user-facing skill, resolve its manifest entry: a `source` file, a `reuse` of another scenario's assembled skill, or `reuse` + a `seam` fragment.
   - `combined`'s `create/update/propose-from-pbi` **reuse `ado`** (the work item lives in ADO).
   - `combined`'s `implement-pbi` **reuses `github`** and substitutes a named source anchor with the ADO PBI→PR link fragment.
   - `combined`'s `close-pbi` is the one fully hand-authored combined file (state → ADO, evidence → GitHub PR).
4. Bundle each used `_lib` script once into its owner skill's `scripts/`; set the frontmatter `name` to the user-facing name; strip the seam anchor everywhere it isn't substituted.
5. Inject portable spec fields (`compatibility` computed from the prose; `scenario`/`generator` provenance merged into `metadata`), then lint every generated `SKILL.md` (no template syntax, no leftover anchor, no retired-backend-skill references, no dispatcher prose, no host/tier/backslash paths) and validate frontmatter against the Agent Skills spec (portable keys only, name/description constraints). Any hit fails the build.

The generator is **non-destructive** to a target's host dirs: it writes/refreshes only the skill folders it owns (the manifest's `common` + each scenario's keys) and prunes only owned folders that don't belong to the chosen scenario. Any other skill folder — the `openspec-*` skills, or a project's own — is left untouched. (Only the throwaway `build/` artifact is fully reset per run.)

Connection details (org/project/team for ADO; owner/repo for GitHub) are still collected per-project by the generated skill on first run and persisted into the matching block of `.dobby/config.json`. For `"combined"`, both blocks must be populated.

The user-facing skill names are preserved deliberately so existing muscle memory and natural-language intents continue to work — only the implementation behind them (flat vs dispatched) changed.

### How dobby and openspec skills fit together

The `dobby-*` and `openspec-*` skills are **complementary**, but dobby does **not** bundle or ship the `openspec-*` skills — they are installed per-project by the OpenSpec CLI itself (`openspec init --tools "claude,github-copilot"`, which writes them straight into `.claude/skills/` and `.github/skills/`). dobby's generator is non-destructive so the two sets coexist. Together they bridge the workflow: `dobby-propose-from-pbi` generates an OpenSpec change directory (`openspec/changes/<name>/`) seeded from a real work item; `openspec-apply-change` then implements the tasks; `dobby-close-pbi` closes the work item when done and (optionally) archives the OpenSpec change.

Keep them current with the OpenSpec CLI (`openspec update`), not through dobby. In this repo the `openspec-*` skill folders under `.claude/skills/` and `.github/skills/` are **gitignored** — run `openspec init` after cloning if you want them locally.

### GitHub close flow is PR-shaped

The github-scenario `dobby-close-pbi` requires an **open PR** that references the target issue (`Closes #<N>`, `Fixes #<N>`, or `Resolves #<N>`). Screenshots and other evidence are committed to the PR branch under `docs/evidence/issue-<N>/` and embedded inline in the PR description. The issue closes automatically when the PR merges — the skill never calls `gh issue close` directly. This is intentional and matches GitHub's idiomatic workflow.

The ADO-scenario close flow is different: it talks to the work item directly and is PR-agnostic. The `combined` close flow splits the difference: work-item state/comments/links go to ADO, while visual evidence is committed to the GitHub PR branch. Each scenario follows its native idiom rather than forcing the trackers to look symmetric.

### Why the Python helpers exist (ADO side)

The `az boards` CLI has hard limitations that the ADO skills work around with several small REST-API scripts. Do not "simplify" by replacing them with `az boards` calls — they exist for specific reasons:

All ADO helper scripts live in `skills/_lib/` and are bundled (once, into an owner skill's `scripts/`) by the generator for any scenario that uses them.

| Script (`skills/_lib/`) | Reason it exists |
|---|---|
| `azdo-update-fields.py` | `az boards work-item create --description` truncates at newlines and cannot set the field format to **Markdown**. This script PATCHes `System.Description` and `Microsoft.VSTS.Common.AcceptanceCriteria` via REST and sets `multilineFieldsFormat` to `Markdown` in the same call. Idempotent. Used by the ADO create / update / propose / close skills. |
| `azdo-add-comment.py` | Posts large markdown comments (with embedded image URLs) to a work item's discussion thread. Reads the body from a file to avoid shell-quoting issues. |
| `azdo-upload-attachment.py` | Uploads image files as work-item attachments and returns their URLs, which then get spliced into the closing comment. |
| `azdo-add-dev-links.py` | Adds Development links (commit / branch / PR) to a work item, choosing between ArtifactLink and Hyperlink based on whether the org's ADO can reach the repo. |
| `azdo-delete-comment.py` | Deletes a work-item comment (used to "edit" a markdown comment by delete-then-repost, avoiding the HTML downgrade bug). |
| `azdo-get-comments.py` | Fetches a work item's discussion thread (used by the ADO update/refine flow). |

All Azure DevOps scripts share the **same auth fallback chain** (`AZURE_DEVOPS_EXT_PAT` → `ADO_TOKEN` → `az account get-access-token`) and the same retry-with-backoff for HTTP 429/502/503/504. Keep that pattern when adding new ADO helper scripts.

### GitHub side has no helper scripts

The `gh` CLI is mature enough that the github-scenario skills shell out directly without any Python intermediaries (the github manifest entries bundle zero `_lib` scripts). `gh issue create --body-file`, `gh issue view --json`, `gh pr edit --body-file` all handle the operations cleanly, and GitHub's markdown rendering is native (no format-flag dance like ADO requires).

### Repo-level helper scripts

| Script | Purpose |
|---|---|
| `scripts/build-skills.py` | The scenario-skill generator. `build` (all → `build/<scenario>/`), `init <target> <scenario>`, `dev` (github → dobby's own `.claude/skills/` + `.github/skills/`). |
| `scripts/check-skill-sync.py` | Verifies dobby's committed host copies match the generator's `dev` (github) output. Exits non-zero with the drifted files on failure. |

### Cross-skill invariants

- **Scenario is fixed at generation, not invocation**: the generator emits a flat, specialized skill set. There is no dispatcher and no runtime `backend` branch. The `backend` key in `.dobby/config.json` is a **record** of which scenario the skills were generated for, not a router.
- **Reuse is explicit in `manifest.json`**: never fork a skill by copying its prose. If `combined` needs `ado`'s behavior, the manifest declares `reuse: "ado"`. `_lib` scripts are bundled once per scenario (de-duped by name) under an owner skill — preserving the shared-by-reference pattern.
- **Generated output is flat and lint-clean**: one `SKILL.md` per user-facing name; no nested `Read … SKILL.md` backend routing, no `backend` branching, no template/macro syntax, no leftover `<!-- dobby:combined-seam:* -->` anchor. The generator's lint enforces this on every run.
- **Generator is non-destructive**: `init`/`dev` manage only dobby-owned skill folders (manifest `common` + scenario keys) and never delete or overwrite foreign folders (openspec-*, a project's own). Safe to re-run on a project that has other skills. Only `build/` is fully reset.
- **dobby does not ship openspec skills**: the `openspec-*` skills are installed per-project by the OpenSpec CLI (`openspec init`), kept current with `openspec update`, and gitignored in this repo. `_common` holds only dobby-authored scenario-independent skills (`grill-*`, `dobby-worktree`).
- **Edit sources, regenerate, commit**: edit under `skills/` (the right tier), run `python scripts/build-skills.py dev`, and commit the regenerated `.claude/skills/` + `.github/skills/`. `check-skill-sync.py` (which compares only dobby-owned skills) fails CI if they drift.
- **Combined mode**: `backend: "combined"` means ADO for work items + GitHub for repo/PRs. Both `ado` and `github` config blocks must be populated, and both identities (`az account show` + `gh auth status`) are verified at the start of the combined skills.
- **GitHub close requires a PR**: the github-scenario `dobby-close-pbi` refuses to proceed unless an open PR references the issue via `Closes #<N>`, `Fixes #<N>`, or `Resolves #<N>`. Closure happens at PR merge, not by `gh issue close`.
- **Two-step ADO PBI creation**: `az boards work-item create` (basic fields) → `azdo-update-fields.py` (markdown body). Never pass `--description` to `az boards work-item create`; it will truncate.
- **Identity displayed early**: every skill that touches a tracker runs `az account show` or `gh auth status` before doing real work so the user can catch wrong-account issues before wasting a flow.
- **Trust user-provided field values**: skills should NOT pre-validate area paths, iterations, labels, or parent IDs against listings if the user supplied them. Attempt the operation, re-prompt only on failure.
- **Never auto-retry creation**: prevents duplicate work items / issues.
- **Markdown templates as the source of structure**: PBI body shape lives in `skills/ado/dobby-create-pbi/templates/pbi-template.md` (one file mapping to two ADO fields). GitHub issue body shape lives in `skills/github/dobby-create-pbi/templates/issue-template.md` (one file with Description + Acceptance Criteria sections, since GitHub has a single body field). Don't inline these structures inside the SKILL.md.

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
# Inspect/edit a skill — these are the "source files" (pick the right tier)
skills/{ado,github,combined,_common}/<skill-name>/SKILL.md
skills/_lib/<script>.py

# After editing a source, regenerate dobby's host copies and verify no drift
python scripts/build-skills.py dev        # or:  .\dobby.ps1 dev   (PowerShell wrapper)
python scripts/check-skill-sync.py        # or:  .\dobby.ps1 check

# Inspect all three scenarios without touching the committed copies
python scripts/build-skills.py build      # → build/<scenario>/ (gitignored)

# Smoke-test a helper script (Python 3, stdlib only — no pip install needed)
python skills/_lib/azdo-update-fields.py --help

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

## OpenSpec workflow

`openspec/config.yaml` declares schema `spec-driven`. Active changes live under `openspec/changes/<name>/` with `proposal.md`, `design.md`, `tasks.md`, and optional delta `specs/`. The `openspec-*` skills wrap the CLI. Backend-specific propose-from skills add traceability:

| Backend | Change name format | Source line in `proposal.md` |
|---|---|---|
| Azure DevOps | `pbi-<id>-<slug>` | `> Source: Azure DevOps PBI [#<id>](<url>) — "<title>"` |
| GitHub | `issue-<id>-<slug>` | `> Source: GitHub Issue [#<id>](<url>) — "<title>"` |

Archived changes go to `openspec/changes/archive/YYYY-MM-DD-<name>/`.

## Conventions specific to this repo

- **Greenfield, no source code yet**: when asked to add functionality, check whether scaffolding exists; if not, propose a structure before generating files. There are no language/framework precedents to follow — ask before introducing any.
- **Commit trailer**: repository policy uses `Co-authored-by: Copilot` on commits.
- **`.dobby/evidence/` is gitignored** because ADO before-capture screenshots may contain sensitive data — never commit anything from that directory.
- **`docs/evidence/issue-<N>/` IS committed**: the GitHub close flow commits screenshots to the PR branch (under `docs/evidence/issue-<N>/`) so GitHub can render them inline in the PR description via `raw.githubusercontent.com`. These files survive PR merge into main. Prune periodically with a housekeeping commit if the directory grows large.
- **`--output json` / `--json` everywhere**: every `az` and `gh` invocation in skill prose uses JSON output for reliable parsing — keep that pattern when adding new commands.
