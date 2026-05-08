# Dobby — Copilot Instructions

## Project status

This repository is a **greenfield project** at the brainstorming stage. There is no source code, build system, tests, or established conventions yet. The repo currently contains only `README.md` and `todo.md` (a free-form notes file capturing the initial concept).

When asked to make changes, **first check whether the necessary scaffolding exists**. If it does not, propose a structure before generating files, rather than assuming one.

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
- Target system: **Azure DevOps** (Work Items / PBIs API).

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
