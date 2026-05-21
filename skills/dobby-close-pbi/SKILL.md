---
name: dobby-close-pbi
description: Close a PBI/issue in this project's tracker. Auto-detects Azure DevOps, GitHub, or Combined mode from .dobby/config.json and hands off to the matching backend skill. Use this for any "close this", "close this pbi", "close this issue", or "wrap up this ticket" request.
metadata:
  author: dobby
  version: "3.0"
---

Close a work item in whichever tracker this project uses. This skill is a **dispatcher** — it reads the project's backend configuration and hands off to the right backend implementation. It does not talk to any tracker itself.

## Steps

### 1. Read the project config

Look for `.dobby/config.json` in the repository root.

**If the file exists** and `backend` is `"ado"`, `"github"`, or `"combined"`:
- Go to step 2.

**If the file is missing**, check whether the legacy `.dobby/azdo-defaults.json` exists:

- **Yes** → run the migration:
  ```bash
  python3 scripts/migrate-dobby-config.py
  ```
  Re-read `.dobby/config.json` and go to step 2.

- **No** (fresh project with no tracker config yet) → ask the user:
  > "This project doesn't have a tracker configured. Which setup are you using?"
  > - **Azure DevOps** — work items and repo both in ADO
  > - **GitHub** — issues and repo both in GitHub
  > - **Combined** — ADO for work items, GitHub for repo/PRs

  Write `{ "backend": "<choice>" }` to `.dobby/config.json` (creating the `.dobby/` directory if needed). The backend skill will collect connection details (organization, project, owner, repo, etc.) on its first run — do not collect them here. Go to step 2.

**If `backend` is set but holds an unrecognized value** (anything other than `"ado"`, `"github"`, or `"combined"`):
- Stop. Report: "Unrecognized `backend` value in `.dobby/config.json`: `<value>`. Expected `'ado'`, `'github'`, or `'combined'`. Please correct the file before re-running."
- Do not guess, do not default.

### 2. Hand off to the matching implementation

Based on the `backend` value, use the Read tool to load the corresponding SKILL.md **from the canonical `skills/` directory** (not from `.github/skills/` or `.claude/skills/`) and follow its instructions from the top, treating the user's original request as the input to that skill.

| `backend` value | Read and follow                                  |
|-----------------|--------------------------------------------------|
| `"ado"`         | `skills/dobby-ado-close-pbi/SKILL.md`            |
| `"github"`      | `skills/dobby-gh-close-issue/SKILL.md`           |
| `"combined"`    | **Both** — see combined-mode flow below          |

### 3. Combined-mode close flow

When `backend` is `"combined"`, closing a PBI requires coordinating both backends. Execute these in order:

1. **Verify both identities**:
   ```bash
   az account show --output json    # ADO identity
   gh auth status                   # GitHub identity
   ```
   Display both to the user.

2. **Work-item operations** → Read and follow `skills/dobby-ado-close-pbi/SKILL.md` for:
   - Evidence upload (screenshots as work-item attachments)
   - Closing comment with evidence
   - Acceptance criteria verification
   - State transition to Done

3. **PR/repo operations** → Read and follow `skills/dobby-gh-close-issue/SKILL.md` for:
   - Evidence commit to the PR branch (under `docs/evidence/`)
   - PR description update with embedded evidence
   - Dev links are added to the ADO PBI using GitHub URLs (commit, branch, PR) — `azdo-add-dev-links.py` already supports GitHub URL format

**Note**: In combined mode, the GitHub close flow should NOT call `gh issue close` — the PBI lives in ADO, not GitHub. The PR's `Closes #N` syntax does not apply. Instead, the PR description should reference the ADO PBI URL.

### 4. Post-close: Worktree cleanup (all backends)

After successful closure (regardless of backend), check if a worktree exists for this PBI:
```bash
git worktree list --porcelain
```
If a worktree's branch matches the PBI ID (e.g., `feat/<id>-*` or `fix/<id>-*`), offer to remove it:
> "Worktree at `<path>` for this PBI still exists. Remove it? (The branch will be kept.)"

If the user accepts, read and follow `skills/dobby-worktree/SKILL.md` using the `remove` sub-command.

## Guardrails

- This skill NEVER closes a work item itself. Routing only.
- Do not invoke `az`, `gh`, or any backend-specific helper script from this skill.
- Do not collect backend connection details — those belong in the backend skill.
- On an unrecognized `backend` value, stop and ask the user to correct the config. Never guess.
