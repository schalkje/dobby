# dobby

Agentic DevOps — a collection of agent **skills** that automate the Azure DevOps PBI lifecycle (create → propose-spec → close-with-evidence) plus generic OpenSpec workflow helpers.

## Prerequisites

You need the OpenSpec CLI installed to use the OpenSpec workflow skills (`openspec-propose`, `openspec-apply-change`, `openspec-archive-change`, `openspec-explore`) and `dobby-propose-from-pbi`.

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

### dobby-create-pbi · Copilot CLI + Claude Code

Creates a Product Backlog Item in Azure DevOps from a conversational request. Collects fields interactively (title, description, project, area path, iteration, parent), validates prerequisites, and creates the work item via the `az boards` CLI.

- **Prerequisites**: Azure CLI with the `azure-devops` extension, authenticated (`az login`); Python 3.
- **Example**: `Create a PBI titled "Add login page" in project MyProject under feature 1234`
- **Source**: [`skills/dobby-create-pbi/SKILL.md`](skills/dobby-create-pbi/SKILL.md)

### dobby-close-pbi · Copilot CLI + Claude Code

Closes a Product Backlog Item in Azure DevOps. Gathers implementation evidence (before/after screenshots, dev links), posts a closing comment, sets state to **Done**, and optionally closes child tasks.

- **Prerequisites**: Azure CLI with the `azure-devops` extension, authenticated (`az login`); Python 3.
- **Example**: `Close PBI 12345 — I added before screenshots earlier and have the after shots ready`
- **Source**: [`skills/dobby-close-pbi/SKILL.md`](skills/dobby-close-pbi/SKILL.md)

### dobby-propose-from-pbi · Copilot CLI + Claude Code

Fetches an Azure DevOps PBI and generates an OpenSpec change (`proposal.md`, `design.md`, `tasks.md`) seeded from the work item, with a traceability line back to the PBI.

- **Prerequisites**: Azure CLI with the `azure-devops` extension, authenticated (`az login`); `openspec` CLI; Python 3.
- **Example**: `Generate an OpenSpec proposal from PBI 12345`
- **Source**: [`skills/dobby-propose-from-pbi/SKILL.md`](skills/dobby-propose-from-pbi/SKILL.md)

### openspec-propose · Copilot CLI + Claude Code

Proposes a new OpenSpec change with proposal, design, specs, and tasks generated in one step. Use when you want to describe what to build and get a complete proposal ready for implementation.

- **Prerequisites**: `openspec` CLI.
- **Example**: `Propose a change: add a rate limiter to the public API`
- **Source**: [`skills/openspec-propose/SKILL.md`](skills/openspec-propose/SKILL.md)

### openspec-apply-change · Copilot CLI + Claude Code

Implements tasks from an existing OpenSpec change. Use to start, continue, or work through the tasks of a proposed change.

- **Prerequisites**: `openspec` CLI.
- **Example**: `Apply the change "add-rate-limiter"`
- **Source**: [`skills/openspec-apply-change/SKILL.md`](skills/openspec-apply-change/SKILL.md)

### openspec-archive-change · Copilot CLI + Claude Code

Archives a completed OpenSpec change once implementation is finished, moving it under `openspec/changes/archive/YYYY-MM-DD-<name>/`.

- **Prerequisites**: `openspec` CLI.
- **Example**: `Archive the change "add-rate-limiter"`
- **Source**: [`skills/openspec-archive-change/SKILL.md`](skills/openspec-archive-change/SKILL.md)

### openspec-explore · Copilot CLI + Claude Code

Explore mode — a thinking partner for working through ideas, investigating problems, and clarifying requirements before or during a change.

- **Prerequisites**: `openspec` CLI.
- **Example**: `Let's explore: what would it take to support multi-tenant queues?`
- **Source**: [`skills/openspec-explore/SKILL.md`](skills/openspec-explore/SKILL.md)

### grill-me · Copilot CLI + Claude Code

Interviews you relentlessly about a plan or design until you reach a shared understanding, walking down each branch of the decision tree.

- **Prerequisites**: None.
- **Example**: `grill me on this plan`
- **Source**: [`skills/grill-me/SKILL.md`](skills/grill-me/SKILL.md)

### grill-pbi · Copilot CLI + Claude Code

Stress-tests a PBI or issue's requirements, acceptance criteria, and scope. Use after creating or refining a work item.

- **Prerequisites**: `az` CLI (ADO) or `gh` CLI (GitHub) for fetching the work item.
- **Example**: `grill this PBI` or `stress-test the requirements for issue 42`
- **Source**: [`skills/grill-pbi/SKILL.md`](skills/grill-pbi/SKILL.md)

### grill-proposal · Copilot CLI + Claude Code

Stress-tests an OpenSpec proposal's scope, goals, and feasibility before implementation begins.

- **Prerequisites**: `openspec` CLI.
- **Example**: `grill this proposal` or `challenge the scope of add-rate-limiter`
- **Source**: [`skills/grill-proposal/SKILL.md`](skills/grill-proposal/SKILL.md)

### grill-design · Copilot CLI + Claude Code

Stress-tests an OpenSpec design's architecture, trade-offs, and implementation risks.

- **Prerequisites**: `openspec` CLI.
- **Example**: `grill this design` or `review the architecture for add-rate-limiter`
- **Source**: [`skills/grill-design/SKILL.md`](skills/grill-design/SKILL.md)
