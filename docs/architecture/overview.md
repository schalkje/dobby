# Dobby — Architecture Overview

Dobby is a **skill library**, not an application. There is no build pipeline, no compiled output, and no runtime of its own. The "code" is a collection of agent **skill definitions** — markdown `SKILL.md` files plus small Python helper scripts — designed to be discovered and executed by AI coding assistants.

## What Dobby does

Dobby automates the work-item lifecycle across two trackers:

- **Azure DevOps** — PBIs (Product Backlog Items), boards, via the `az` CLI
- **GitHub** — Issues, PRs, via the `gh` CLI

The lifecycle covers: **create → update/refine → propose spec → implement → close with evidence**.

Dobby also bundles OpenSpec workflow wrappers and standalone conversational skills for design review.

## Skill categories

Skills fall into three categories:

| Category | Skills | Purpose |
|---|---|---|
| **Tracker** | `dobby-create-pbi`, `dobby-close-pbi`, `dobby-update-pbi`, `dobby-propose-from-pbi` + their ADO/GitHub backends | Work-item CRUD and lifecycle across ADO and GitHub |
| **OpenSpec wrappers** | `openspec-propose`, `openspec-apply-change`, `openspec-archive-change`, `openspec-explore` | Wrap the external `openspec` CLI for spec-driven development |
| **Conversational** | `grill-me` (+ future variations) | Standalone interrogative design review and stress-testing |

## Skill catalog

### Public skills (user-facing)

These are the skills users invoke directly. Tracker dispatchers route to the correct backend automatically.

| Skill | Type | Description |
|---|---|---|
| `dobby-create-pbi` | Dispatcher | Create a work item (PBI or Issue) |
| `dobby-close-pbi` | Dispatcher | Close a work item with evidence |
| `dobby-update-pbi` | Dispatcher | Update/refine an existing work item |
| `dobby-propose-from-pbi` | Dispatcher | Generate an OpenSpec proposal from a work item |
| `openspec-propose` | Wrapper | Propose a new OpenSpec change |
| `openspec-apply-change` | Wrapper | Implement tasks from an OpenSpec change |
| `openspec-archive-change` | Wrapper | Archive a completed change |
| `openspec-explore` | Wrapper | Thinking partner / explore mode |
| `grill-me` | Conversational | Stress-test a plan or design |

### Internal skills (backend implementations)

These are invoked by dispatchers, never directly by users.

| Skill | Backend | Dispatcher |
|---|---|---|
| `dobby-ado-create-pbi` | Azure DevOps | `dobby-create-pbi` |
| `dobby-ado-close-pbi` | Azure DevOps | `dobby-close-pbi` |
| `dobby-ado-update-pbi` | Azure DevOps | `dobby-update-pbi` |
| `dobby-ado-propose-from-pbi` | Azure DevOps | `dobby-propose-from-pbi` |
| `dobby-gh-create-issue` | GitHub | `dobby-create-pbi` |
| `dobby-gh-close-issue` | GitHub | `dobby-close-pbi` |
| `dobby-gh-propose-from-issue` | GitHub | `dobby-propose-from-pbi` |

> **Note:** `dobby-update-pbi` does not yet have a GitHub backend.

## High-level routing

```
User intent ("close this PBI")
        │
        ▼
  ┌─────────────┐
  │  Dispatcher  │  dobby-close-pbi
  │  (public)    │  Reads .dobby/config.json
  └──────┬──────┘
         │
    ┌────┴────┐
    │ backend │
    │  field  │
    ▼         ▼
┌────────┐ ┌────────┐
│  ADO   │ │ GitHub │
│backend │ │backend │
└────┬───┘ └───┬────┘
     │         │
     ▼         ▼
  az CLI     gh CLI
     │         │
     ▼         ▼
Azure DevOps  GitHub
  (REST API)  (GraphQL/REST)
```

## End-to-end workflow

The Dobby skills and OpenSpec skills serve different phases of the development lifecycle. Dobby handles the **work-item management** phase (talking to ADO/GitHub), and OpenSpec handles the **implementation** phase (spec-driven coding). The `propose-from-pbi` skill bridges the two.

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: Work-item management (Dobby tracker skills)          │
│                                                                 │
│  create-pbi ──► update/refine ──► propose-from-pbi ────────┐   │
│       │              │                    │                  │   │
│       ▼              ▼                    │                  │   │
│   az/gh CLI      az/gh CLI               │                  │   │
│       │              │                    │                  │   │
│       ▼              ▼                    │                  │   │
│   ADO / GitHub   ADO / GitHub            │                  │   │
└──────────────────────────────────────────┼──────────────────┘   │
                                           │                      │
                                           ▼                      │
┌──────────────────────────────────────────────────────────────┐  │
│  Phase 2: Implementation (OpenSpec wrapper skills)           │  │
│                                                              │  │
│  openspec-propose ──► openspec-apply-change                  │  │
│       │                     │                                │  │
│       ▼                     ▼                                │  │
│  openspec CLI          openspec CLI                          │  │
│  (proposal.md,         (implement tasks)                     │  │
│   design.md,                │                                │  │
│   tasks.md)                 ▼                                │  │
│                     openspec-archive-change                  │  │
└──────────────────────────────────────────────────────────────┘  │
                                                                  │
┌──────────────────────────────────────────────────────────────┐  │
│  Phase 3: Closure (Dobby tracker skills)                     │  │
│                                                              │  │
│  close-pbi ──► az/gh CLI ──► ADO / GitHub                 ◄─┘  │
│  (evidence, screenshots, dev links, state change)            │  │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Cross-cutting: Conversational skills                        │
│                                                              │
│  grill-me ──► stress-test any plan/design at any phase       │
│              (explores codebase, no tracker/CLI dependency)   │
└──────────────────────────────────────────────────────────────┘
```

### Key insight

- **Dobby tracker skills** are the interface to the external trackers (ADO, GitHub). They use `az` and `gh` CLIs to read and write work items.
- **OpenSpec** is the main deliverable format for the implementation phase. It is an external tool with its own update cycle — Dobby wraps it but does not manage it.
- **The bridge** is `dobby-propose-from-pbi`: it reads a refined work item from the tracker and generates the OpenSpec change directory that drives implementation.
- **Conversational skills** like `grill-me` can be used at any phase to stress-test plans and designs.

## Source of truth and host discovery

Skills have one canonical location and two generated copies:

```
skills/<name>/          ← canonical source (edit here)
        │
        │  sync-skills.py
        ▼
.github/skills/<name>/ ← Copilot CLI discovery (generated)
.claude/skills/<name>/ ← Claude Code discovery (generated)
```

Generated copies carry a "do not edit" notice pointing back to the canonical source. See [Contributing](contributing.md) for the sync workflow.

## Runtime dependencies

| Dependency | Required by | Notes |
|---|---|---|
| `az` CLI + `azure-devops` ext | ADO backend skills | `az login` for auth |
| `gh` CLI | GitHub backend skills | `gh auth login` for auth |
| Python 3 (stdlib only) | ADO helper scripts, sync scripts | No pip packages |
| `openspec` CLI | OpenSpec wrapper skills, propose-from-pbi | External tool, own update cycle |
