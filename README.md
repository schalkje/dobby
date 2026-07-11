# dobby

Agentic DevOps — a collection of agent **skills** that automate the work-item lifecycle (create → propose-spec → implement → close-with-evidence) across **Azure DevOps** (PBIs) and **GitHub** (Issues). A project targets one scenario (`ado`, `github`, or `combined`) and dobby assembles a flat, specialized skill set for it.

## Prerequisites

The `dobby-propose-from-pbi` skill and the OpenSpec workflow depend on the OpenSpec CLI. dobby does **not** bundle the `openspec-*` workflow skills — those are installed per-project by the OpenSpec CLI itself (see [Configure skills for your project](#configure-skills-for-your-project)). You still need the CLI on PATH for both.

### Install OpenSpec CLI

Install from npm:

```bash
npm install -g @openspec/cli
```

If you prefer not to install globally, use `npx`:

```bash
npx @openspec/cli --help
```

Verify the installation:

```bash
openspec --version
openspec list --json
```

If the `openspec` command is not found after global install, restart your terminal so your PATH updates.

## Configure skills for your project

A project targets one **scenario** — `ado` (Azure DevOps), `github`, or `combined` (GitHub repo/PRs + ADO boards). Dobby assembles a flat, specialized skill set for that scenario; there is no runtime backend dispatcher.

On Windows/PowerShell, the `dobby.ps1` wrapper in the repo root is the easiest entry point:

```powershell
.\dobby.ps1 init                                    # interactive: prompts for target + scenario
.\dobby.ps1 init ..\my-app github                   # scaffold the github scenario into ..\my-app
.\dobby.ps1 init ..\my-app github -Config -OpenSpec # + config skeleton + install OpenSpec skills
```

`init` writes the scenario's skills into the target project's `.claude/skills/` (Claude Code) and `.github/skills/` (GitHub Copilot CLI). It is **non-destructive** — it manages only dobby's own skills and leaves anything else in those dirs untouched, so it's safe to re-run. The equivalent without the wrapper is `python scripts/build-skills.py init <target> <scenario>`.

**OpenSpec skills are separate.** dobby does not bundle the `openspec-*` workflow skills; install them per-project with the OpenSpec CLI (`dobby.ps1 init -OpenSpec` runs this for you, or do it manually):

```bash
openspec init --tools "claude,github-copilot"       # run in the target project
```

## Skill layout

Skills are **assembled per scenario at build time** from three source tiers under `skills/`:

| Path | Role |
|---|---|
| [`skills/_lib/`](skills/) | Shared helper scripts, bundled into a scenario only when used. |
| [`skills/_common/`](skills/) | Scenario-independent, dobby-authored skills (`grill-*`, `dobby-worktree`), copied into every scenario. |
| [`skills/{ado,github,combined}/`](skills/) | Scenario-specialized prose, under the user-facing names. |
| [`skills/manifest.json`](skills/manifest.json) | The assembly contract (source / reuse per scenario). |
| `.github/skills/<name>/`, `.claude/skills/<name>/` | **Generated** host-discovery copies (dobby's own = the github scenario). Do not edit. |

After editing any source, regenerate dobby's own copies with `python scripts/build-skills.py dev` (or `.\dobby.ps1 dev`) before committing, and verify a clean tree with `python scripts/check-skill-sync.py` (or `.\dobby.ps1 check`).

See [`scripts/README.md`](scripts/README.md) for the generator modes, the manifest schema, and the `dobby.ps1` wrapper.

## Skill catalog

The catalog below is dobby's own skill set — the **github** scenario (issues + PRs), which is what dobby generates for itself. An `ado` or `combined` project gets the same user-facing names, specialized for that scenario; the descriptions here would read "PBI"/"Azure DevOps" instead of "issue"/"GitHub". Each entry links to its **source** tier (`skills/github/…` for backend-specialized prose, `skills/_common/…` for scenario-independent skills) — not the generated host copies under `.claude/skills/` and `.github/skills/`, which you never edit directly.

### dobby-create-pbi · Copilot CLI + Claude Code

Creates a GitHub Issue from a conversational request. Collects fields interactively (title, Description, Acceptance Criteria, labels, parent), validates prerequisites, and creates the issue via the `gh` CLI.

- **Prerequisites**: `gh` CLI, authenticated (`gh auth login`).
- **Example**: `Create an issue titled "Add login page" with acceptance criteria for happy path and validation`
- **Source**: [`skills/github/dobby-create-pbi/SKILL.md`](skills/github/dobby-create-pbi/SKILL.md)

### dobby-update-pbi · Copilot CLI + Claude Code

Updates or refines a GitHub Issue's body (Description + Acceptance Criteria) via `gh issue edit`. Refinement mode synthesizes the existing body, discussion comments, and codebase context into a well-structured issue.

- **Prerequisites**: `gh` CLI, authenticated (`gh auth login`).
- **Example**: `Refine issue 42` or `update the acceptance criteria on issue 42`
- **Source**: [`skills/github/dobby-update-pbi/SKILL.md`](skills/github/dobby-update-pbi/SKILL.md)

### dobby-propose-from-pbi · Copilot CLI + Claude Code

Fetches a GitHub Issue and generates an OpenSpec change (`proposal.md`, `design.md`, `tasks.md`) seeded from the issue, with a traceability line back to it.

- **Prerequisites**: `gh` CLI, authenticated (`gh auth login`); `openspec` CLI.
- **Example**: `Generate an OpenSpec proposal from issue 42`
- **Source**: [`skills/github/dobby-propose-from-pbi/SKILL.md`](skills/github/dobby-propose-from-pbi/SKILL.md)

### dobby-implement-pbi · Copilot CLI + Claude Code

End-to-end lifecycle orchestrator: from branch creation through spec, implementation, evidence capture, PR, and closure. An adaptive checklist with resume/skip support. Delegates to `dobby-worktree` for the branch step when worktrees are enabled.

- **Prerequisites**: `gh` CLI, authenticated; `openspec` CLI; `git`.
- **Example**: `Implement from issue: https://github.com/owner/repo/issues/42`
- **Source**: [`skills/github/dobby-implement-pbi/SKILL.md`](skills/github/dobby-implement-pbi/SKILL.md)

### dobby-close-pbi · Copilot CLI + Claude Code

Closes a GitHub Issue through its Pull Request: requires an open PR referencing the issue (`Closes #N`), commits before/after evidence to the PR branch under `docs/evidence/issue-<N>/`, embeds it inline in the PR description, and relies on close-on-merge (never calls `gh issue close`).

- **Prerequisites**: `gh` CLI, authenticated; an open PR that references the issue; `git`.
- **Example**: `Close issue 42 — the PR is open and I have the after screenshots ready`
- **Source**: [`skills/github/dobby-close-pbi/SKILL.md`](skills/github/dobby-close-pbi/SKILL.md)

### dobby-worktree · Copilot CLI + Claude Code

Manages git worktrees for parallel PBI development — create, list, and remove worktrees tied to work items. Used standalone or invoked by `dobby-implement-pbi` when `worktree.enabled` is set in `.dobby/config.json`.

- **Prerequisites**: `git`.
- **Example**: `Create a worktree for issue 42` or `list worktrees`
- **Source**: [`skills/_common/dobby-worktree/SKILL.md`](skills/_common/dobby-worktree/SKILL.md)

### grill-me · Copilot CLI + Claude Code

Interviews you relentlessly about a plan or design until you reach a shared understanding, walking down each branch of the decision tree.

- **Prerequisites**: None.
- **Example**: `grill me on this plan`
- **Source**: [`skills/_common/grill-me/SKILL.md`](skills/_common/grill-me/SKILL.md)

### grill-pbi · Copilot CLI + Claude Code

Stress-tests a PBI or issue's requirements, acceptance criteria, and scope. Use after creating or refining a work item.

- **Prerequisites**: `gh` CLI (GitHub) or `az` CLI (ADO) for fetching the work item.
- **Example**: `grill this PBI` or `stress-test the requirements for issue 42`
- **Source**: [`skills/_common/grill-pbi/SKILL.md`](skills/_common/grill-pbi/SKILL.md)

### grill-proposal · Copilot CLI + Claude Code

Stress-tests an OpenSpec proposal's scope, goals, and feasibility before implementation begins.

- **Prerequisites**: `openspec` CLI.
- **Example**: `grill this proposal` or `challenge the scope of add-rate-limiter`
- **Source**: [`skills/_common/grill-proposal/SKILL.md`](skills/_common/grill-proposal/SKILL.md)

### grill-design · Copilot CLI + Claude Code

Stress-tests an OpenSpec design's architecture, trade-offs, and implementation risks.

- **Prerequisites**: `openspec` CLI.
- **Example**: `grill this design` or `review the architecture for add-rate-limiter`
- **Source**: [`skills/_common/grill-design/SKILL.md`](skills/_common/grill-design/SKILL.md)
