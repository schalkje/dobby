## Context

Today `dobby-implement-pbi` creates branches with `git checkout -b <branch>`, which forces serial development — starting a new PBI means stashing or committing in-progress work. Git worktrees allow multiple working directories sharing the same `.git` store, enabling parallel PBI work with separate agent sessions.

The current `.dobby/config.json` supports `backend: "ado"` or `"github"`, but a common scenario uses **ADO for work items** and **GitHub for the repository/PRs**. This "combined" mode needs explicit support in the dispatcher routing layer and config schema.

### Current branch creation (Phase 1 of `dobby-implement-pbi`)
```
git checkout main && git pull
git checkout -b feat/<id>-<slug>
```

### Current dispatcher routing
```
config.backend ──┬── "ado"    → dobby-ado-*
                 └── "github" → dobby-gh-*
```

## Goals / Non-Goals

**Goals:**
- Enable parallel PBI development via git worktrees — each PBI gets its own working directory
- Support a "combined" backend where ADO handles work items and GitHub handles repo/PR operations
- Keep worktree usage optional — `git checkout -b` remains the default for simplicity
- Provide worktree lifecycle management (create, list, remove) as a standalone skill
- Integrate worktree creation into `dobby-implement-pbi` Phase 1 when enabled

**Non-Goals:**
- Automatic worktree cleanup on a schedule (manual or PBI-close-triggered only)
- Supporting more than two backends simultaneously (e.g., ADO + GitHub + GitLab)
- IDE/editor workspace management (opening worktrees in VS Code, etc.)
- Worktree-per-task (only worktree-per-PBI; individual tasks within a PBI share the worktree)

## Decisions

### 1. Worktree directory layout — sibling directory with configurable root

Worktrees are created as sibling directories to the main repo:

```
C:\repo\jeroen\dobby\                    ← main worktree (stays on main/develop)
C:\repo\jeroen\dobby-worktrees\          ← worktree root (configurable)
  ├── feat-123-add-auth\                 ← worktree = branch for PBI 123
  ├── fix-456-login-bug\                 ← worktree = branch for PBI 456
  └── feat-789-dashboard\               ← worktree = branch for PBI 789
```

**Why sibling, not nested**: Nested worktrees inside the repo would show up in `git status` and need `.gitignore` entries. Sibling keeps them cleanly separated.

**Default root**: `<repo-parent>/<repo-name>-worktrees/`. Configurable via `.dobby/config.json` → `worktree.root`.

**Alternatives considered**:
- Fixed sibling directory (`../worktrees/`) — too generic, collides if multiple repos share a parent
- Inside `.git/worktrees/` — that's where git stores metadata, not working directories
- User home directory — too far from the project, breaks relative-path assumptions

### 2. Worktree naming convention — branch name as directory name

The worktree directory name matches the branch name (with `/` replaced by `-`):
- Branch `feat/123-add-auth` → directory `feat-123-add-auth`
- Branch `fix/456-login-bug` → directory `fix-456-login-bug`

This makes it easy to find worktrees by PBI ID (`ls | grep 123`).

### 3. Combined backend config shape — extend existing config

```json
{
  "backend": "combined",
  "ado": {
    "organization": "https://dev.azure.com/org/",
    "project": "MyProject",
    "team": "MyTeam"
  },
  "github": {
    "owner": "org",
    "repo": "my-repo"
  },
  "worktree": {
    "enabled": true,
    "root": "../my-repo-worktrees"
  }
}
```

**Routing for `combined`**: The dispatcher determines which backend to call based on the *operation type*, not a single backend:

```
Operation type          Routes to
─────────────────────   ──────────────────────
Work item CRUD          dobby-ado-*
(create, update, close, 
 read PBI, comments, 
 evidence upload)

Repo operations         dobby-gh-*
(branch, PR, commit 
 evidence to branch)
```

**Why not a separate `repo` config block**: The `github` block already exists for the GitHub backend. Reusing it when `backend: "combined"` avoids schema duplication. The `ado` block similarly already exists.

**Alternative considered**: `backend: "ado"` with an additional `repo.host: "github"` — this hides the combined nature and makes dispatcher logic messier (checking two fields instead of one).

### 4. Worktree skill as standalone — `dobby-worktree`

A new skill `dobby-worktree` handles:
- `create` — create a worktree for a PBI (branch + directory)
- `list` — show active worktrees and their associated PBIs
- `remove` — clean up a worktree (after PBI close or on demand)

`dobby-implement-pbi` Phase 1 checks if worktrees are enabled and delegates to `dobby-worktree` instead of running `git checkout -b`.

**Why standalone**: Worktree management is useful independently (user might want to set up a worktree without running the full implement lifecycle).

### 5. `.dobby/` in worktrees — config shared, evidence isolated

Git worktrees share the `.git` directory but have independent working trees. Since `.dobby/config.json` is tracked in git, it's shared across worktrees automatically. `.dobby/evidence/` is gitignored, so it's per-worktree — each PBI's evidence stays isolated.

This is exactly the right behavior without any extra work.

### 6. Combined-mode close flow — split operations

When closing a PBI in combined mode:
1. **Evidence upload** → ADO (`azdo-upload-attachment.py`, `azdo-add-comment.py`)
2. **Acceptance criteria, state transition** → ADO (`az boards work-item update`)
3. **PR creation/update** → GitHub (`gh pr create`, `gh pr edit`)
4. **Evidence commit to PR branch** → GitHub (git commit + push)
5. **Dev links** → ADO (`azdo-add-dev-links.py` with GitHub URLs — already supported)

The close dispatcher for combined mode orchestrates both backend skills sequentially rather than handing off entirely to one.

## Risks / Trade-offs

- **[Complexity]** Combined mode adds a third routing path to every dispatcher → Mitigation: Keep dispatcher logic minimal; the combined dispatcher calls ADO skills for work-item ops and GitHub skills for repo ops in sequence.
- **[Worktree state drift]** Worktrees can get out of sync with `main` if not regularly rebased → Mitigation: `dobby-worktree list` shows last-updated timestamp; `dobby-implement-pbi` warns if the worktree is behind main.
- **[Stale worktrees]** Users forget to clean up → Mitigation: `dobby-close-pbi` offers to remove the worktree after successful closure. `dobby-worktree list` highlights stale worktrees (no commits in 7+ days).
- **[Windows path length]** Deep worktree paths on Windows can hit 260-char limit → Mitigation: Use short directory names (branch slug, not full path). Document `git config core.longpaths true` as a prerequisite.
- **[Agent CWD assumption]** Copilot/Claude sessions assume CWD is the repo root → Mitigation: When working in a worktree, the worktree IS the repo root from git's perspective. `.git` file (not directory) points to the main repo's `.git/worktrees/<name>/`. All git commands work normally.
