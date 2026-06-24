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

## Project tracker config

Every dobby skill reads `.dobby/config.json` to learn which tracker the project uses (Azure DevOps or GitHub) and the per-backend connection details. The shape is:

```jsonc
{
  // Routing key. Required. One of "ado", "github", or "combined".
  // "combined" means ADO for work items + GitHub for repo/PRs.
  "backend": "ado",

  // Populated when backend = "ado" or "combined".
  // Mirrors the old azdo-defaults.json.
  "ado": {
    "organization": "https://dev.azure.com/myorg/",
    "project": "MyProject",
    "team": "MyTeam",
    "devLinks": {
      "repoReachableFromAdo": true,
      "host": "github",
      "githubConnectionId": "<guid>",
      "adoProjectId": "<guid>",
      "adoRepoId": "<guid>"
    }
  },

  // Populated when backend = "github" or "combined".
  "github": {
    "owner": "vanlanschot",
    "repo": "strada",
    "defaultLabels": ["needs-triage"],
    "projectNumber": 7
  },

  // Optional. Controls git-worktree-based parallel development.
  // When enabled, each PBI gets its own worktree directory instead
  // of using `git checkout -b`.
  "worktree": {
    "enabled": false,
    // Custom worktree root. Default: <repo-parent>/<repo-name>-worktrees/
    "root": "../my-repo-worktrees"
  }
}
```

For `"ado"` or `"github"` backends, only the active backend's block is required. For `"combined"`, both `ado` and `github` blocks must be populated. The `worktree` block is optional for any backend.

### `migrate-dobby-config.py`

One-time migration from the legacy `.dobby/azdo-defaults.json` to the new `.dobby/config.json`. Reads the legacy file, wraps its contents in `{ "backend": "ado", "ado": <legacy> }`, writes the new file, and removes the legacy file only after the new file is written successfully.

```bash
python scripts/migrate-dobby-config.py              # migrate this project
python scripts/migrate-dobby-config.py --dry-run    # print result, don't write
python scripts/migrate-dobby-config.py --force      # allow overwriting existing config.json
```

Idempotent — safe to re-run. If `.dobby/config.json` already exists the script exits 0 with an "already migrated" message and changes nothing. If neither file exists (a fresh checkout) the script exits 0 without doing anything.

Dispatcher skills run this automatically on first invocation when they detect a legacy file with no new file.

## Why these scripts exist

Symlinks would work on macOS/Linux but are fragile on Windows (the primary dev OS for this repo) and aren't always preserved by git. A small copy-and-check pair is cross-platform and gives a clear failure mode (the check script names the drifted file).
