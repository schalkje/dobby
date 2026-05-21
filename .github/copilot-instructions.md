# Dobby — Copilot Instructions

## Project status

This repository is a collection of **agent skill definitions** (markdown `SKILL.md` files plus small Python helper scripts) that automate the work-item lifecycle (Azure DevOps PBIs and/or GitHub Issues) and wrap the OpenSpec workflow. There is no build, test, or lint pipeline — the "code" is the skill prompts and their helpers.

The project supports three backend modes configured via `.dobby/config.json`:
- **`"ado"`** — Azure DevOps for both work items and repo
- **`"github"`** — GitHub for both issues and repo
- **`"combined"`** — ADO for work items, GitHub for repo/PRs

Git worktree support (`dobby-worktree` skill) enables parallel PBI development — each PBI gets its own working directory. Opt-in via `"worktree": { "enabled": true }` in config.

When asked to make changes, first check whether the necessary scaffolding exists. If it does not, propose a structure before generating files, rather than assuming one.

## Skill layout

Every skill has one canonical folder and two host-discovery copies:

| Path | Role |
|---|---|
| `skills/<name>/` | **Canonical source.** Edit only here. |
| `.github/skills/<name>/` | Copy for GitHub Copilot CLI discovery. Do not edit. |
| `.claude/skills/<name>/` | Copy for Claude Code discovery. Do not edit. |

Each host copy of a `SKILL.md` carries a notice immediately after the YAML frontmatter pointing back at the canonical source.

After any edit under `skills/<name>/`, regenerate the host copies before committing:

```bash
python scripts/sync-skills.py            # regenerate .github/skills/ and .claude/skills/
python scripts/check-skill-sync.py       # verify no drift (exits non-zero on drift)
```

See [`scripts/README.md`](../scripts/README.md) for details.

## Project intent (from `todo.md`)

Dobby is intended to be an **agentic DevOps assistant for Azure DevOps**, focused on the PBI (Product Backlog Item) lifecycle:

1. **PO stage** — create an initial PBI from a short description and/or email.
2. **Refinement stage** — interactive refinement session (user + agent) that expands the PBI into a comprehensive piece of work.
3. **Planning stage** — developer-driven breakdown into tasks.
4. **Implementation stage** — agent assists the developer with closing tasks and capturing testing evidence.

These stages are distinct **processes/agents**, not a single monolithic flow. Treat them as separate concerns when designing modules.

## Stated technology preferences

- Methodology: **OpenSpec** (the user explicitly wants the project structured this way — confirm OpenSpec conventions before scaffolding).
- AI runtime: **GitHub Copilot / Azure** (prefer these over other LLM providers when adding integrations).
- UI: not yet decided — must be easily accessible, clear, and interactive. Do not assume a framework; ask before introducing one.
- Target system: **Azure DevOps** (Work Items / PBIs API), **GitHub** (Issues API), or **Combined** (ADO work items + GitHub repo).

## Conventions for working in this repo

- `todo.md` is a **brainstorming scratchpad**, not a spec. Do not treat statements there as finalized requirements; surface ambiguities back to the user.
- When introducing new tooling (language, package manager, framework, linter), **ask first** — there are no precedents to follow yet.
- Keep `README.md` updated as real structure lands; right now it is a single-line placeholder.
- Use the `Co-authored-by: Copilot` trailer on commits per repository policy.

## What does NOT exist yet (do not assume)

- No build, test, or lint commands.
- No CI workflows.
- No source directories, package manifest, or dependency lockfile.
- No architecture — the four-stage process above is intent, not implemented design.
