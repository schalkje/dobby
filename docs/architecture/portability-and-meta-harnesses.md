# Portability invariants and the meta-harness position

Status: decided 2026-07-11 (issue #12). Revisit triggers at the bottom.

## Context

"Meta-harnesses" sit above individual agent harnesses (Claude Code, Copilot
CLI, Codex, …) and add cross-vendor routing, governance policies (spend caps,
approval gates), sandboxed parallel execution, and shared/steerable sessions.
The reference point is [Omnigent](https://github.com/omnigent-ai/omnigent)
(Databricks, open-sourced June 2026, Apache-2.0): its portable unit — the
"agent image" — is a directory of `config.yaml` + `AGENTS.md` +
`skills/<name>/SKILL.md` + `tools/`. That skills payload is exactly the flat,
scenario-specialized skill set dobby's generator already emits.

Meanwhile, both of dobby's host harnesses grew first-party orchestration:
Claude Code agent teams + dynamic workflows, and GitHub Agent HQ / mission
control.

## Decision: adopt the patterns, not the dependency

1. **No meta-harness integration now.** Omnigent is weeks old (v0.x, weekly
   breaking releases) and nothing in dobby's lifecycle requires cross-vendor
   orchestration. Dobby's flows are deliberately interactive (identity checks,
   confirmation gates, grills), which fights fire-and-forget orchestration,
   and sandboxed execution complicates the authenticated `az`/`gh` CLI
   prerequisites.
2. **The patterns are adopted natively instead**:
   - parallel isolation → `dobby-worktree` (one worktree per PBI);
   - governance → identity-displayed-early, confirm-before-create/close,
     never-auto-retry (dobby's local equivalents of policy gates);
   - fan-out-friendly structure → `dobby-implement-pbi`'s phase checklist and
     progress ledger work as a task plan for host-native agent teams.
3. **Compatibility is kept free by invariants, not integration.** As long as
   the invariants below hold, any meta-harness that consumes SKILL.md
   directories can consume a dobby scenario build unchanged.

## Portability invariants (enforced; do not regress)

These are what make a dobby scenario build consumable by any spec-conforming
host or meta-harness. All but the last are enforced by the generator's
lint/validation (`scripts/build-skills.py`); treat them as hard requirements
when authoring skills:

1. **Flat generated skill sets** — one `skills/<name>/SKILL.md` per user-facing
   skill; no nested routing, no dispatcher.
2. **Spec-portable frontmatter only** — the agentskills.io key set; no
   host-specific extensions in generated output.
3. **No host-specific paths** — skills reference each other by name; bundled
   files resolve relative to the installed skill set; forward slashes only.
4. **Stdlib-only Python helpers** — no pip installs; scripts are self-contained
   inside the skill directory.
5. **Per-project state stays in `.dobby/`** — never in the harness's own
   directories, so the same project works under any host.

## Revisit triggers

- Omnigent (or a comparable meta-harness) reaches **v1.0 with a stable agent-
  image spec**, or a dobby user asks to run dobby scenarios under one.
- Action when triggered: add an `omnigent` (or generic agent-image) **output
  mode to `scripts/build-skills.py`** that wraps a scenario build in the
  image directory layout. Estimated at roughly a day of work on top of the
  existing manifest/scenario system — an output format, not an architecture
  change. Track it as a new issue when the trigger fires.
