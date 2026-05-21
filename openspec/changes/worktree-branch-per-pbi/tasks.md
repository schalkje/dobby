## 1. Config Schema Extension

- [ ] 1.1 Update `.dobby/config.json` schema to accept `"combined"` as a valid `backend` value alongside `"ado"` and `"github"`
- [ ] 1.2 Add optional `worktree` block to config schema with `enabled` (boolean, default `false`) and `root` (string, optional custom path)
- [ ] 1.3 Update `scripts/migrate-dobby-config.py` to preserve the new fields if present and document the extended schema in `scripts/README.md`

## 2. Combined Backend Dispatchers

- [ ] 2.1 Update `skills/dobby-create-pbi/SKILL.md` to handle `backend: "combined"` — route work-item creation to `dobby-ado-create-pbi`
- [ ] 2.2 Update `skills/dobby-close-pbi/SKILL.md` to handle `backend: "combined"` — route work-item ops to ADO, PR/evidence-commit ops to GitHub
- [ ] 2.3 Update `skills/dobby-propose-from-pbi/SKILL.md` to handle `backend: "combined"` — fetch PBI from ADO, generate OpenSpec change with ADO traceability
- [ ] 2.4 Update first-run interactive prompt in all three dispatchers to offer "Combined (ADO work items + GitHub repo)" as a third option
- [ ] 2.5 Add dual identity verification (both `az account show` and `gh auth status`) at start of combined-mode operations

## 3. Worktree Skill

- [ ] 3.1 Create `skills/dobby-worktree/SKILL.md` with `create`, `list`, and `remove` sub-commands
- [ ] 3.2 Implement `create` logic: `git fetch origin` → `git worktree add <root>/<branch-slug> -b <branch> origin/main`, with PBI ID and title as input
- [ ] 3.3 Implement `list` logic: parse `git worktree list --porcelain`, extract PBI IDs from branch names, flag stale worktrees (no commits in 7+ days)
- [ ] 3.4 Implement `remove` logic: find worktree by PBI ID, warn on uncommitted changes, `git worktree remove [--force]`
- [ ] 3.5 Read `worktree.root` from `.dobby/config.json` (default: `<repo-parent>/<repo-name>-worktrees/`)

## 4. Integrate Worktrees into Implement Lifecycle

- [ ] 4.1 Update `skills/dobby-implement-pbi/SKILL.md` Phase 1 to check `worktree.enabled` in config — if true, delegate to `dobby-worktree create` instead of `git checkout -b`
- [ ] 4.2 Update `skills/dobby-implement-pbi/SKILL.md` Phase 0 (detect existing state) to check for existing worktree via `git worktree list`
- [ ] 4.3 Add worktree cleanup offer to `dobby-close-pbi` dispatchers — after successful close, if a worktree exists for the PBI, offer to remove it

## 5. Sync and Verify

- [ ] 5.1 Run `python scripts/sync-skills.py` to regenerate `.github/skills/` and `.claude/skills/` host copies
- [ ] 5.2 Run `python scripts/check-skill-sync.py` to verify no drift between canonical and host copies
- [ ] 5.3 Update `CLAUDE.md` and `.github/copilot-instructions.md` with combined-backend and worktree documentation
