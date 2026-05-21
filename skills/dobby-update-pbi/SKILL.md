---
name: dobby-update-pbi
description: Update/refine a PBI, Bug, or Feature in this project's tracker. Auto-detects Azure DevOps vs GitHub from .dobby/config.json and hands off to the matching backend skill. Use this for any "update pbi", "refine pbi", "improve pbi", "update description", "update acceptance criteria", "fix pbi fields", or "make this PBI better" request.
metadata:
  author: dobby
  version: "1.1"
---

Update or refine a work item in whichever tracker this project uses. This skill is a **dispatcher** — it reads the project's backend configuration and hands off to the right backend implementation. It does not talk to any tracker itself.

## Steps

### 1. Read the project config

Look for `.dobby/config.json` in the repository root.

**If the file exists** and `backend` is `"ado"` or `"github"`:
- Go to step 2.

**If the file is missing**, check whether the legacy `.dobby/azdo-defaults.json` exists:

- **Yes** → run the migration:
  ```bash
  python3 scripts/migrate-dobby-config.py
  ```
  Re-read `.dobby/config.json` and go to step 2.

- **No** (fresh project with no tracker config yet) → ask the user:
  > "This project doesn't have a tracker configured. Are you using Azure DevOps or GitHub?"

  Write `{ "backend": "<choice>" }` to `.dobby/config.json` (creating the `.dobby/` directory if needed). The backend skill will collect connection details (organization, project, owner, repo, etc.) on its first run — do not collect them here. Go to step 2.

**If `backend` is set but holds an unrecognized value** (anything other than `"ado"` or `"github"`):
- Stop. Report: "Unrecognized `backend` value in `.dobby/config.json`: `<value>`. Expected `'ado'` or `'github'`. Please correct the file before re-running."
- Do not guess, do not default.

### 2. Hand off to the matching implementation

Based on the `backend` value, use the Read tool to load the corresponding SKILL.md and follow its instructions from the top, treating the user's original request as the input to that skill.

| `backend` value | Read and follow                                  |
|-----------------|--------------------------------------------------|
| `"ado"`         | `skills/dobby-ado-update-pbi/SKILL.md`           |
| `"github"`      | *(not yet implemented — stop and notify user)*   |

## Guardrails

- This skill NEVER updates a work item itself. Routing only.
- Do not invoke `az`, `gh`, or any backend-specific helper script from this skill.
- Do not collect backend connection details — those belong in the backend skill.
- On an unrecognized `backend` value, stop and ask the user to correct the config. Never guess.
