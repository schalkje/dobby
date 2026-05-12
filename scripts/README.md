# scripts/

Repository-level helper scripts. Python stdlib only — no pip install required.

## Skill sync

Dobby skills have one canonical location and two host-discovery copies:

| Path | Role |
|---|---|
| `skills/<name>/` | **Canonical source.** Edit only here. |
| `.github/skills/<name>/` | Copy for GitHub Copilot CLI discovery. Do not edit. |
| `.claude/skills/<name>/` | Copy for Claude Code discovery. Do not edit. |

Two scripts keep the copies aligned with the source:

### `sync-skills.py`

Walks `skills/`, copies each `<name>/` to both `.github/skills/<name>/` and `.claude/skills/<name>/`, prepends a "do not edit — this is a copy" notice to every SKILL.md (after the YAML frontmatter), and removes any folders from the host directories that no longer exist in `skills/`.

```bash
python scripts/sync-skills.py          # sync; print one line per skill per host
python scripts/sync-skills.py --quiet  # sync silently
```

Run this **before committing any skill edit**.

### `check-skill-sync.py`

Regenerates into a temp directory and diffs against the on-disk host copies. Exits 0 if everything matches; exits non-zero with the list of drifted files and the exact fix command otherwise.

```bash
python scripts/check-skill-sync.py
```

Use this to verify a clean tree (e.g., before pushing, or as a pre-commit hook if you choose to install one — none is installed by default).

## Why these scripts exist

Symlinks would work on macOS/Linux but are fragile on Windows (the primary dev OS for this repo) and aren't always preserved by git. A small copy-and-check pair is cross-platform and gives a clear failure mode (the check script names the drifted file).
