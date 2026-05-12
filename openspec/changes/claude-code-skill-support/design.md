## Context

Dobby today targets a single host — **GitHub Copilot CLI** — which discovers skills under `.github/skills/<name>/SKILL.md`. The author also uses **Claude Code**, which discovers skills under `.claude/skills/<name>/SKILL.md`. The two paths are not interchangeable, but the SKILL.md format is essentially the same shape on both (YAML frontmatter + markdown body), and the procedural content of every dobby skill is host-neutral (it issues `az`, `python`, `git`, `openspec` shell commands).

The smallest thing that solves the user problem is: **one canonical skill folder, copied to each host's discovery path**.

## Goals / Non-Goals

**Goals:**
- One folder per skill is the single source of truth.
- Both Copilot CLI and Claude Code can discover and run every skill when working in this repo.
- A copy-and-check workflow keeps the two host views in sync.
- Documentation tells contributors which folder to edit and how to sync.

**Non-Goals:**
- No generator, templating, or per-host preamble system. If a single skill ever needs real per-host tuning, it gets a small hand-edit and a comment explaining why — not infrastructure.
- No CI integration. The repo has no CI today; the sync check is a documented manual step (and is suitable for a pre-commit hook later if the author wants one).
- No support for hosts beyond Copilot CLI and Claude Code.

## Decisions

### 1. Canonical location: `skills/<name>/`

**Decision**: A new top-level `skills/` directory holds the canonical skill source. Each skill is one folder containing its `SKILL.md`, `scripts/`, and `templates/`.

**Why a top-level `skills/`** (rather than nesting under `.github/skills/` or `.claude/skills/`): the canonical source is host-neutral, so it shouldn't live under either host's namespace. The two host paths are deployment targets, not the source.

### 2. Host-discovery copies under `.github/skills/` and `.claude/skills/`

**Decision**: `.github/skills/<name>/` and `.claude/skills/<name>/` each contain a copy of `skills/<name>/`. These copies are checked into git so that anyone who clones the repo and opens it in either host immediately sees the skills — no install step required.

**Copy, not symlink**: symlinks work on macOS/Linux but are fragile on Windows (the dev OS for this repo) and are not preserved by default in some git workflows. Copying is the simplest cross-platform option and the user explicitly accepted it.

**These copies are not leading code.** They exist only so the two hosts can discover the skills while working on dobby itself. The first lines of every copied SKILL.md note this explicitly: *"This file is a copy of `skills/<name>/SKILL.md` — edit the source, not this copy."*

### 3. Sync mechanism: a copy script and a check script

**Decision**: 
- `scripts/sync-skills.py`: walks `skills/`, copies each `<name>/` to both `.github/skills/<name>/` and `.claude/skills/<name>/`. Prepends a "copy of skills/<name>/ — do not edit" notice after the YAML frontmatter on copy.
- `scripts/check-skill-sync.py`: runs the sync into a temp directory, diffs against on-disk copies, exits non-zero on drift with a one-liner telling the contributor what to run.

Both scripts are stdlib-only Python (consistent with the existing `azdo-*.py` helpers).

**Why scripts not just `cp -r`**: cross-platform (Windows + macOS + Linux all work the same), and the "do not edit" notice insertion is mechanical.

### 4. Helper-script paths

**Decision**: SKILL.md content refers to helper scripts by their **canonical** path (`skills/<name>/scripts/<script>.py`), not by the host-specific copy path. After sync, both host copies of the SKILL.md point at the same physical script files via the canonical path. The script files themselves also get copied alongside the SKILL.md (so each host directory is a working unit), but the invocation in the SKILL.md prose targets the canonical location to make the source-of-truth obvious.

**Rationale**: avoids ambiguity about which copy of a script is being executed (there's only one canonical script; the host-copies are for discoverability), and means a stale or hand-edited host-copy doesn't silently win.

**Alternative considered — only copy SKILL.md, not scripts**: rejected because some host environments may sandbox skill execution to the skill's own directory. Copying the full folder keeps everything self-contained while the SKILL.md prose anchors execution to the canonical path.

### 5. Host-specific tuning, when needed

**Decision**: the SKILL.md body stays host-neutral by default. When a real difference must be called out (e.g., "Claude Code's AskUserQuestion tool accepts a different option shape than Copilot's"), the SKILL.md mentions both inline in a single sentence. No generator, no templating, no per-host file.

**Why this is fine**: surveying the existing skills, host-specific tool references are rare and confined to a handful of decision points. Most skills mention generic concepts ("ask the user", "track progress") that map naturally onto both hosts' tools. The few real divergences (slash-command names, specific tool schemas) can be handled with a sentence each.

**If a real divergence ever forces a fork** (e.g., one host can do something the other can't), the contributor edits the host-copy by hand and adds a comment explaining the divergence. The sync check then ignores that specific file. This is YAGNI for now — we don't pre-build the override mechanism.

### 6. Documentation

**Decision**:
- `README.md` gets a full skill catalog: every skill, one-line description, hosts, prerequisites, one minimal usage example.
- `CLAUDE.md` and `.github/copilot-instructions.md` get a "Skill layout" section that says: edit `skills/<name>/`, run `python scripts/sync-skills.py` before committing, the `.github/` and `.claude/` copies are not leading code.

## Risks / Trade-offs

- **[Contributor edits a host copy instead of the source]** → "do not edit" notice in the copy header + sync check catches it next run.
- **[Generated copies create noisy diffs in PRs]** → in practice the copies change only when the source changes; each skill edit produces predictable triple-file diffs (source + 2 copies). Reviewable.
- **[Disk duplication]** → ~3× the on-disk footprint of skill content. Each SKILL.md is small; the helper Python scripts are ~50–300 lines each. Negligible for this repo.
- **[A host adds a discovery path we don't sync to]** → handled by adding one more target to the sync script. Trivial.

## Migration Plan

1. Create `skills/` and move each skill folder from `.github/skills/<name>/` to `skills/<name>/`.
2. Write `scripts/sync-skills.py` and `scripts/check-skill-sync.py`.
3. Run the sync to populate `.github/skills/` (re-establishing the Copilot view) and `.claude/skills/` (new — establishing the Claude Code view).
4. Update `README.md`, `CLAUDE.md`, and `.github/copilot-instructions.md`.
5. Verify by listing skills in both Copilot CLI and Claude Code and invoking one (e.g., `dobby-create-pbi --help`-style smoke check).

## Open Questions

- **`.github/prompts/opsx-*.prompt.md`**: these duplicate the `openspec-*` skills' content for slash-prompt invocation in Copilot. Keep as-is; out of scope for this change.
