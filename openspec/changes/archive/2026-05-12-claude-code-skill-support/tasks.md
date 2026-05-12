## 1. Canonical Layout

- [x] 1.1 Create top-level `skills/` directory
- [x] 1.2 Move each existing skill from `.github/skills/<name>/` to `skills/<name>/` (preserve `scripts/` and `templates/` subfolders): `dobby-create-pbi`, `dobby-close-pbi`, `dobby-propose-from-pbi`, `grill-me`, `openspec-propose`, `openspec-apply-change`, `openspec-archive-change`, `openspec-explore`
- [x] 1.3 Inside each `skills/<name>/SKILL.md`, rewrite every helper-script and template reference to use the canonical path (`skills/<name>/scripts/...`, `skills/<name>/templates/...`) — including the cross-skill reference from `dobby-propose-from-pbi` and `dobby-close-pbi` into `dobby-create-pbi`'s helper

## 2. Sync and Check Scripts

- [x] 2.1 Write `scripts/sync-skills.py`: walks `skills/`, copies each `<name>/` to `.github/skills/<name>/` and `.claude/skills/<name>/`; for SKILL.md files it inserts a "This file is a copy of `skills/<name>/SKILL.md` — edit the source, not this copy." notice immediately after the closing YAML frontmatter delimiter; copies helper scripts and templates verbatim; removes folders from the host directories that are not present in `skills/`
- [x] 2.2 Write `scripts/check-skill-sync.py`: regenerates into a temp directory, diffs against the on-disk host copies, exits non-zero with an actionable message identifying drifted files and naming the fix command
- [x] 2.3 Both scripts use Python stdlib only — no third-party imports (matches repo convention for `azdo-*.py`)
- [x] 2.4 Write `scripts/README.md` explaining the generator/checker pair, how to run them, and the convention that host copies are not edited directly

## 3. Run the Sync

- [x] 3.1 Execute `python scripts/sync-skills.py`
- [x] 3.2 Verify each `.github/skills/<name>/SKILL.md` and `.claude/skills/<name>/SKILL.md` exists and contains the "do not edit" notice
- [x] 3.3 Run `python scripts/check-skill-sync.py` and confirm exit 0
- [x] 3.4 Spot-check: open one regenerated Copilot SKILL.md and verify the only differences from the canonical are the "do not edit" notice

## 4. Documentation

- [x] 4.1 Rewrite the Skills section of `README.md` as a catalog covering every skill: name, one-line description, hosts (Copilot CLI, Claude Code, or both), prerequisites, one minimal usage example, link to `skills/<name>/SKILL.md`
- [x] 4.2 Add a "Skill layout" section to `CLAUDE.md`: `skills/<name>/` is the canonical source; `.github/skills/` and `.claude/skills/` are copies; run `python scripts/sync-skills.py` before committing skill edits; run `python scripts/check-skill-sync.py` to verify
- [x] 4.3 Update the "Why the Python helpers exist" table in `CLAUDE.md` to reference the canonical script paths (`skills/<name>/scripts/...`)
- [x] 4.4 Mirror the "Skill layout" section into `.github/copilot-instructions.md` so Copilot contributors see the same rules

## 5. Verification

- [x] 5.1 Final run of `python scripts/check-skill-sync.py` exits 0 on a clean tree
- [x] 5.2 Drift test: hand-edit a generated SKILL.md, re-run the check script, confirm non-zero exit with an actionable message, revert the hand-edit, re-run, confirm 0
- [x] 5.3 Confirm `git status` shows: new `skills/` tree, regenerated `.github/skills/` with "do not edit" notice prepended to each SKILL.md, new `.claude/skills/` tree, new `scripts/` directory, updated `README.md` / `CLAUDE.md` / `.github/copilot-instructions.md`
