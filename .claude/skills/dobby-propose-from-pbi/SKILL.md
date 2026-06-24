---
name: dobby-propose-from-pbi
description: Generate an OpenSpec change proposal from a PBI/issue in this project's tracker. Auto-detects Azure DevOps, GitHub, or Combined mode from .dobby/config.json and hands off to the matching backend skill. Use this for any "spec from pbi", "propose from issue", or "create a proposal for ticket" request.
metadata:
  author: dobby
  version: "3.0"
---

<!-- This file is a copy of `skills/dobby-propose-from-pbi/SKILL.md` — edit the source, not this copy. Regenerate with `python scripts/sync-skills.py`. -->

Generate an OpenSpec change proposal from a work item in whichever tracker this project uses. This skill is a **dispatcher** — it reads the project's backend configuration and hands off to the right backend implementation. It does not talk to any tracker itself.

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

| `backend` value | Read and follow                                       |
|-----------------|-------------------------------------------------------|
| `"ado"`         | `skills/dobby-ado-propose-from-pbi/SKILL.md`          |
| `"github"`      | `skills/dobby-gh-propose-from-issue/SKILL.md`         |
| `"combined"`    | `skills/dobby-ado-propose-from-pbi/SKILL.md` *(PBI lives in ADO)* |

**Combined mode note**: For `"combined"`, the work item lives in ADO, so the proposal is generated from the ADO PBI. Before handing off, verify both identities:
```bash
az account show --output json    # ADO identity
gh auth status                   # GitHub identity
```
Display both to the user so they can catch wrong-account issues early.

## Guardrails

- This skill NEVER generates the proposal itself. Routing only.
- Do not invoke `az`, `gh`, `openspec`, or any backend-specific helper script from this skill.
- Do not collect backend connection details — those belong in the backend skill.
- On an unrecognized `backend` value, stop and ask the user to correct the config. Never guess.
