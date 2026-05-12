# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Dobby is **not an application** — there is no build, test, or lint pipeline. It is a collection of agent **skill definitions** (markdown `SKILL.md` files plus a few small Python helper scripts) that automate the Azure DevOps PBI lifecycle (create → propose-spec → close-with-evidence) via the `az` CLI and the Azure DevOps REST API.

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

Two parallel skill families, both anchored on a shared defaults file:

```
.dobby/azdo-defaults.json   ← single source of truth for org / project / team
                              read by every dobby-* skill before anything else

skills/                     ← canonical source for all skills
├── dobby-create-pbi/         ← conversational PBI creation in Azure DevOps
├── dobby-propose-from-pbi/   ← fetch a PBI and generate an OpenSpec change from it
├── dobby-close-pbi/          ← close a PBI, attach evidence (before/after screenshots)
├── grill-me/                 ← interview the user to stress-test a plan
└── openspec-{propose,apply-change,archive-change,explore}/   ← generic OpenSpec CLI workflow skills

.github/skills/   ← generated copies for Copilot CLI discovery
.claude/skills/   ← generated copies for Claude Code discovery
```

The `dobby-*` and `openspec-*` skills are **complementary**: `dobby-propose-from-pbi` bridges the two by generating an OpenSpec change directory (`openspec/changes/<name>/`) seeded from a real PBI; `openspec-apply-change` then implements the tasks; `dobby-close-pbi` closes the PBI when done and (optionally) archives the OpenSpec change.

### Why the Python helpers exist

The `az boards` CLI has hard limitations that the skills work around with three small REST-API scripts. Do not "simplify" by replacing them with `az boards` calls — they exist for specific reasons:

| Script | Reason it exists |
|---|---|
| `skills/dobby-create-pbi/scripts/azdo-update-fields.py` | `az boards work-item create --description` truncates at newlines and cannot set the field format to **Markdown**. This script PATCHes `System.Description` and `Microsoft.VSTS.Common.AcceptanceCriteria` via REST and sets `multilineFieldsFormat` to `Markdown` in the same call. Idempotent — safe to re-run with the same work-item ID. |
| `skills/dobby-close-pbi/scripts/azdo-add-comment.py` | Posts large markdown comments (with embedded image URLs) to a work item's discussion thread. Reads the body from a file to avoid shell-quoting issues. |
| `skills/dobby-close-pbi/scripts/azdo-upload-attachment.py` | Uploads image files as work-item attachments and returns their URLs, which then get spliced into the closing comment. |
| `skills/dobby-close-pbi/scripts/evidence-store.py` | Local-only: stages before/after screenshots under `.dobby/evidence/<work-item-id>/{before,after}/` (gitignored — may contain sensitive data). |

All three Azure DevOps scripts share the **same auth fallback chain** (`AZURE_DEVOPS_EXT_PAT` → `ADO_TOKEN` → `az account get-access-token`) and the same retry-with-backoff for HTTP 429/502/503/504. Keep that pattern when adding new helper scripts.

### Cross-skill invariants

- **Defaults flow**: every dobby skill loads `.dobby/azdo-defaults.json` first, falls back to `az devops configure --list`, and only prompts as a last resort. File defaults take priority over CLI defaults. `dobby-create-pbi` writes this file at the end of its first successful run.
- **Two-step PBI creation**: `az boards work-item create` (basic fields) → `azdo-update-fields.py` (markdown body). Never pass `--description` to `az boards work-item create`; it will truncate.
- **Identity displayed early**: every skill runs `az account show` before doing real work so the user can catch wrong-account issues before wasting a flow.
- **Trust user-provided field values**: skills should NOT pre-validate area paths, iterations, or parent IDs against listings if the user supplied them. Attempt the operation, re-prompt only on failure.
- **Never auto-retry creation**: prevents duplicate work items.
- **Markdown templates as the source of structure**: PBI body shape lives in `skills/dobby-create-pbi/templates/pbi-template.md` (one file mapping to two ADO fields — `System.Description` and `Microsoft.VSTS.Common.AcceptanceCriteria`). Don't inline this structure inside the SKILL.md.

## Common operations

There is no build or test suite. The repo is operated through skill invocations — when working here you typically:

```bash
# Inspect/edit a skill — these are the "source files"
skills/<skill-name>/SKILL.md

# After editing a skill, sync host copies (Copilot CLI + Claude Code)
python scripts/sync-skills.py
python scripts/check-skill-sync.py     # verify no drift

# Smoke-test a helper script (Python 3, stdlib only — no pip install needed)
python skills/dobby-create-pbi/scripts/azdo-update-fields.py --help
python skills/dobby-close-pbi/scripts/evidence-store.py list --work-item-id <id>

# OpenSpec CLI (required for openspec-* and dobby-propose-from-pbi)
openspec list --json
openspec status --change "<name>" --json
openspec new change "<name>"
openspec instructions <artifact-id> --change "<name>" --json
```

Required prerequisites for end-to-end runs: `az` CLI with the `azure-devops` extension (`az extension add --name azure-devops`), authenticated (`az login`); Python 3 (stdlib only); `openspec` CLI for the OpenSpec workflows.

## OpenSpec workflow

`openspec/config.yaml` declares schema `spec-driven`. Active changes live under `openspec/changes/<name>/` with `proposal.md`, `design.md`, `tasks.md`, and optional delta `specs/`. The `openspec-*` skills wrap the CLI; `dobby-propose-from-pbi` adds a "Source: Azure DevOps PBI #..." traceability line to the generated `proposal.md` and uses `pbi-<id>-<slug>` as the change name. Archived changes go to `openspec/changes/archive/YYYY-MM-DD-<name>/`.

## Conventions specific to this repo

- **Greenfield, no source code yet**: when asked to add functionality, check whether scaffolding exists; if not, propose a structure before generating files. There are no language/framework precedents to follow — ask before introducing any.
- **`todo.md` is a brainstorming scratchpad, not a spec**: don't treat statements there as finalized requirements. Surface ambiguities back to the user.
- **Commit trailer**: repository policy uses `Co-authored-by: Copilot` on commits.
- **`.dobby/evidence/` is gitignored** because screenshots may contain sensitive data — never commit anything from that directory.
- **`--output json` everywhere**: every `az` invocation in skill prose uses JSON output for reliable parsing — keep that pattern when adding new commands.
