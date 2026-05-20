# Tracker Integration

This document covers how Dobby's tracker skills interact with Azure DevOps and GitHub.

## Backend resolution

Every tracker operation starts at a **dispatcher** skill, which reads `.dobby/config.json` to determine the active backend:

```json
{
  "backend": "ado",
  "ado": {
    "organization": "https://dev.azure.com/myorg/",
    "project": "MyProject",
    "team": "MyTeam"
  },
  "github": {
    "owner": "my-org",
    "repo": "my-repo"
  }
}
```

### Resolution rules

1. Read `.dobby/config.json`
2. If missing but `.dobby/azdo-defaults.json` exists → run `scripts/migrate-dobby-config.py` to migrate
3. If missing entirely → ask the user "Azure DevOps or GitHub?" and persist their answer
4. If `backend` holds an unrecognized value → **stop and ask** (never guess)
5. Load the matching backend skill and follow its instructions

### Config ownership

- The **dispatcher** only reads the `backend` field for routing
- The **backend skill** owns its connection-detail block (`ado` or `github`) and collects missing values on first run

## Azure DevOps backend

### Auth chain

All ADO backend skills and helper scripts use the same auth fallback:

1. `AZURE_DEVOPS_EXT_PAT` environment variable
2. `ADO_TOKEN` environment variable
3. `az account get-access-token` (interactive login)

Every ADO skill runs `az account show` early so the user can catch wrong-account issues before any mutation.

### CLI limitations and helper scripts

The `az boards` CLI has hard limitations that the ADO skills work around with Python REST-API scripts:

| Script | Why it exists |
|---|---|
| `azdo-update-fields.py` | `az boards work-item create --description` truncates at newlines and cannot set Markdown format. PATCHes fields via REST. |
| `azdo-add-comment.py` | Posts large markdown comments with embedded images. Reads body from file to avoid shell-quoting issues. |
| `azdo-upload-attachment.py` | Uploads images as work-item attachments, returns URLs for splicing into comments. |
| `azdo-add-dev-links.py` | Adds Development links (commit/branch/PR). Chooses ArtifactLink vs Hyperlink based on ADO reachability. |
| `azdo-delete-comment.py` | Deletes a comment from a work item's discussion thread. |
| `evidence-store.py` | Stages before/after screenshots locally under `.dobby/evidence/` (gitignored). |

All scripts share: `--help` support, JSON output, retry-with-backoff on 429/502/503/504.

### Two-step PBI creation

ADO PBI creation is always two steps:

1. `az boards work-item create` — basic fields (title, type, area, iteration, parent)
2. `azdo-update-fields.py` — PATCH the markdown body fields (Description, Acceptance Criteria) and set `multilineFieldsFormat` to `Markdown`

**Never** pass `--description` to `az boards work-item create` — it truncates.

### Work-item hierarchy

ADO enforces a strict hierarchy: `Epic → Feature → PBI → Task`. The create skill validates this and prevents invalid nesting (e.g., PBI under PBI).

## GitHub backend

### Auth and CLI

GitHub backend skills use `gh` CLI directly — no Python helper scripts needed. The `gh` CLI is mature enough for all operations:

- `gh issue create --body-file`
- `gh issue view --json`
- `gh pr edit --body-file`
- `gh issue list --json`

Every GitHub skill runs `gh auth status` early for identity verification.

### PR-based closure

`dobby-gh-close-issue` follows GitHub's idiomatic workflow:

1. **Requires an open PR** that references the target issue (`Closes #N`, `Fixes #N`, or `Resolves #N`)
2. Screenshots and evidence are **committed to the PR branch** under `docs/evidence/issue-<N>/`
3. Evidence images are embedded in the PR description via `raw.githubusercontent.com` URLs
4. The issue closes **automatically when the PR merges** — the skill never calls `gh issue close`

This is deliberate: it matches how GitHub developers expect closure to work.

### Issue body structure

GitHub issues use a single body field (unlike ADO's separate Description and Acceptance Criteria fields). The template puts both sections in one markdown document.

### Parent linkage

GitHub doesn't have native parent-child hierarchy like ADO. Parent linkage uses **task-list references**: `- [ ] #N` in the parent issue body.

## Cross-backend invariants

These rules apply to all tracker interactions regardless of backend:

| Rule | Rationale |
|---|---|
| **JSON output everywhere** | `--output json` / `--json` on every `az`/`gh` call for reliable parsing |
| **Never auto-retry creation** | Prevents duplicate work items / issues |
| **Trust user-provided values** | Don't pre-validate area paths, iterations, labels, or parent IDs — attempt the operation, re-prompt only on failure |
| **Identity displayed early** | `az account show` or `gh auth status` before any real work |
| **Dispatchers never call APIs** | All `az`, `gh`, REST, and script calls live in backend skills only |
| **Markdown everywhere** | All multiline content uses markdown formatting |
