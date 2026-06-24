# Skill Anatomy

This document explains the structural patterns that make up a Dobby skill.

## What makes a skill

At minimum, a skill is a single `SKILL.md` file in a folder under `skills/<name>/`. Skills may also include helper scripts and templates:

```
skills/<name>/
├── SKILL.md              # Required — the prompt definition
├── templates/            # Optional — markdown templates for generated content
│   └── pbi-template.md
└── scripts/              # Optional — Python helper scripts
    └── some-helper.py
```

### SKILL.md structure

Every `SKILL.md` starts with YAML frontmatter:

```yaml
---
name: skill-name
description: One-line description used by host discovery for matching user intent.
---
```

The body after the frontmatter is the prompt that the AI agent follows when the skill is invoked. It contains step-by-step instructions, rules, error handling, and references to templates/scripts.

### Templates

Templates are markdown files that define the shape of generated content (PBI descriptions, issue bodies, etc.). The SKILL.md references them by path. This keeps structure separate from logic.

### Helper scripts

Python scripts (stdlib only, no pip dependencies) that work around CLI limitations. They follow a common pattern:

- Accept `--help` for self-documentation
- Use the shared auth fallback chain (ADO): `AZURE_DEVOPS_EXT_PAT` → `ADO_TOKEN` → `az account get-access-token`
- Retry with backoff on HTTP 429/502/503/504
- Output JSON for reliable parsing by the agent

## Skill patterns

Dobby uses four distinct skill patterns:

### 1. Dispatcher pattern

**Used by:** `dobby-create-pbi`, `dobby-close-pbi`, `dobby-update-pbi`, `dobby-propose-from-pbi`

Dispatchers are the public-facing skills. They never call tracker APIs directly. Their sole job is routing:

1. Read `.dobby/config.json`
2. If missing but legacy `azdo-defaults.json` exists → migrate
3. If missing entirely → ask the user for backend choice and persist
4. If `backend` is unrecognized → stop, ask the user to fix
5. Load the matching backend skill's `SKILL.md` and follow it

This keeps user-facing skill names stable (`dobby-create-pbi`) regardless of which backend is active.

### 2. Backend pattern

**Used by:** `dobby-ado-*`, `dobby-gh-*`

Backend skills are internal — invoked only by dispatchers. They own:

- **Identity verification** — run `az account show` or `gh auth status` early so the user can catch wrong-account issues
- **Connection-detail collection** — org/project/team (ADO) or owner/repo (GitHub), persisted to `.dobby/config.json`
- **API calls** — all `az`, `gh`, REST, and helper-script invocations live here
- **Backend-specific idioms** — ADO's two-step creation, GitHub's PR-based closure

Each backend follows its tracker's native patterns rather than forcing symmetry.

### 3. OpenSpec wrapper pattern

**Used by:** `openspec-propose`, `openspec-apply-change`, `openspec-archive-change`, `openspec-explore`

These wrap the external `openspec` CLI. They:

- Call `openspec list --json`, `openspec status --change ... --json`, `openspec instructions ... --json`
- Interpret the CLI's JSON output (context, rules, templates, dependencies)
- Manage artifacts in `openspec/changes/<name>/`
- Never modify the OpenSpec CLI or its config — they are consumers only

### 4. Conversational pattern

**Used by:** `grill-me` (and future variations)

Conversational skills are standalone — no tracker integration built in, no CLI dependencies. They are pure agent behavior:

- Define a **conversation loop** (ask questions, one at a time)
- Explore the codebase when a question can be answered from code
- Drive toward a **shared understanding** through structured interrogation
- Can be integrated into workflows (e.g., called from tracker or OpenSpec skills)

See [Conversational Skills](conversational-skills.md) for the full framework.

## Naming conventions

| Type | Pattern | Examples |
|---|---|---|
| Public dispatcher | `dobby-<verb>-pbi` | `dobby-create-pbi`, `dobby-close-pbi` |
| ADO backend | `dobby-ado-<verb>-pbi` | `dobby-ado-create-pbi` |
| GitHub backend | `dobby-gh-<verb>-issue` | `dobby-gh-create-issue` |
| OpenSpec wrapper | `openspec-<verb>` | `openspec-propose`, `openspec-apply-change` |
| Conversational | descriptive name | `grill-me` |

Dispatcher names use "pbi" as the generic term (not "issue") because the library originated with Azure DevOps. GitHub backends translate this to "issue" internally.
