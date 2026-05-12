# dobby

Agentic DevOps — a collection of agent **skills** that automate the Azure DevOps PBI lifecycle (create → propose-spec → close-with-evidence) plus generic OpenSpec workflow helpers.

## Skill layout

Every skill has one canonical source folder and two host-discovery copies:

| Path | Role |
|---|---|
| [`skills/<name>/`](skills/) | Canonical source. **Edit only here.** |
| `.github/skills/<name>/` | Copy for **GitHub Copilot CLI** discovery. Generated. |
| `.claude/skills/<name>/` | Copy for **Claude Code** discovery. Generated. |

After editing any skill, run `python scripts/sync-skills.py` before committing. To verify a clean tree, run `python scripts/check-skill-sync.py` (exits non-zero on drift).

See [`scripts/README.md`](scripts/README.md) for details.

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
