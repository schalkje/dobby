## Why

Today `dobby-implement-pbi` creates feature branches with `git checkout -b`, which blocks parallel work — you can't start PBI 456 while PBI 123 is in progress without stashing or committing incomplete work. Git worktrees solve this by giving each PBI its own working directory while sharing the same `.git` store, enabling true parallel development with multiple agent sessions.

Additionally, the current config model assumes a single backend (`"ado"` or `"github"`), but a common real-world setup uses **ADO for work items** and **GitHub for the repository and PRs**. This combined scenario needs first-class support.

## What Changes

- **New `dobby-worktree` skill** that creates, lists, and removes git worktrees for PBIs. Branches are created inside worktrees instead of `git checkout -b`.
- **`dobby-implement-pbi` Phase 1 updated** to delegate branch creation to `dobby-worktree` instead of doing `git checkout -b` directly. Falls back to `checkout -b` when worktrees are disabled.
- **New `"combined"` backend mode** in `.dobby/config.json` where `ado` provides work-item tracking and `github` provides repo/PR operations. The dispatcher routes work-item calls to ADO and repo/PR calls to GitHub.
- **Updated dispatcher routing** in `dobby-create-pbi`, `dobby-close-pbi`, and `dobby-propose-from-pbi` to handle `backend: "combined"` — work-item operations go to ADO skills, PR/branch/evidence-commit operations go to GitHub skills.
- **Worktree lifecycle management** — automatic cleanup option when a PBI is closed (`dobby-close-pbi` offers to remove the worktree after closure).

## Capabilities

### New Capabilities
- `worktree-management`: Creating, listing, and removing git worktrees tied to PBI/issue identifiers. Includes worktree directory naming convention, location strategy, and lifecycle hooks.
- `combined-backend`: Support for `backend: "combined"` in `.dobby/config.json` where work items live in ADO and repository/PRs live in GitHub. Includes dispatcher routing logic and config schema extension.

### Modified Capabilities
- `backend-routing`: Dispatchers must handle `backend: "combined"` in addition to `"ado"` and `"github"`, routing work-item operations to ADO and repo operations to GitHub.

## Impact

- **Skills affected**: `dobby-implement-pbi` (Phase 1 branch creation), all three dispatchers (`dobby-create-pbi`, `dobby-close-pbi`, `dobby-propose-from-pbi`), `dobby-ado-close-pbi` (worktree cleanup hook).
- **Config schema**: `.dobby/config.json` gains `"combined"` as a valid backend value, and a new optional `worktree` config block.
- **File system**: Worktrees create sibling directories (e.g., `../dobby-wt/feat-123-slug/`). The `.dobby/evidence/` directory stays per-worktree (isolated), while `.dobby/config.json` is shared via git.
- **No new dependencies**: Uses only `git worktree` (built-in) and existing `az`/`gh` CLIs.
