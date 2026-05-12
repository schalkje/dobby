## 1. Config schema and migration

- [ ] 1.1 Document the `.dobby/config.json` schema in `scripts/README.md` (top-level `backend`, plus `ado` and `github` blocks) with a fully populated example for each backend
- [ ] 1.2 Implement `scripts/migrate-dobby-config.py` (stdlib only) that reads `.dobby/azdo-defaults.json`, wraps its contents in `{ "backend": "ado", "ado": { ... } }`, writes `.dobby/config.json`, and removes the legacy file only after the new file is written
- [ ] 1.3 Add `--dry-run` flag to the migration script that prints the resulting config without writing
- [ ] 1.4 Add `--force` flag to the migration script that allows overwriting an existing `config.json` (disabled by default)
- [ ] 1.5 Make the migration script idempotent — a second run when `config.json` already exists exits cleanly with a "already migrated" message
- [ ] 1.6 Manually run the migration script against this repo's existing `.dobby/azdo-defaults.json` and verify the output

## 2. Dispatcher skills

- [ ] 2.1 Rewrite `skills/dobby-create-pbi/SKILL.md` as a dispatcher (~30 lines): read config → prompt for missing `backend` → run migration if legacy file present → Read and follow `skills/dobby-ado-create-pbi/SKILL.md` or `skills/dobby-gh-create-issue/SKILL.md`
- [ ] 2.2 Rewrite `skills/dobby-close-pbi/SKILL.md` as a dispatcher routing to `dobby-ado-close-pbi` or `dobby-gh-close-issue`
- [ ] 2.3 Rewrite `skills/dobby-propose-from-pbi/SKILL.md` as a dispatcher routing to `dobby-ado-propose-from-pbi` or `dobby-gh-propose-from-issue`
- [ ] 2.4 In all three dispatchers, set the `description` field to clearly state "auto-detects backend from .dobby/config.json" and list the natural-language phrases handled
- [ ] 2.5 In all three dispatchers, add a guardrail that stops when `backend` holds an unrecognized value rather than guessing

## 3. ADO backend skill extraction

- [ ] 3.1 Create `skills/dobby-ado-create-pbi/` and move the current `dobby-create-pbi` body into it (SKILL.md, scripts/, templates/)
- [ ] 3.2 Update its `description` to begin with "Internal — creates a PBI in Azure DevOps. Invoked by dobby-create-pbi after backend resolution."
- [ ] 3.3 Update SKILL.md to read connection details from `.dobby/config.json` `ado` block instead of `.dobby/azdo-defaults.json`
- [ ] 3.4 Create `skills/dobby-ado-close-pbi/` and move the current `dobby-close-pbi` body (SKILL.md, scripts/) into it with the same description and config-path updates
- [ ] 3.5 Create `skills/dobby-ado-propose-from-pbi/` and move the current `dobby-propose-from-pbi` body into it with the same description and config-path updates
- [ ] 3.6 Update internal references to helper scripts inside the moved SKILL.md files to use their new paths (e.g., `skills/dobby-ado-create-pbi/scripts/azdo-update-fields.py`)
- [ ] 3.7 Cross-check that no SKILL.md in `dobby-ado-*` still references `.dobby/azdo-defaults.json` — all reads/writes go through `.dobby/config.json`

## 4. GitHub backend skills

- [ ] 4.1 Create `skills/dobby-gh-create-issue/SKILL.md` covering: prerequisite check (`gh --version`, `gh auth status`), repo coordinate collection on first run, interactive collection of title/description/AC/labels, issue creation via `gh issue create`, optional parent linkage via task-list reference, output of issue number + URL
- [ ] 4.2 Define a body template for GitHub issues (single markdown body with `## Description` and `## Acceptance Criteria` sections) at `skills/dobby-gh-create-issue/templates/issue-template.md`
- [ ] 4.3 Create `skills/dobby-gh-close-issue/SKILL.md` covering: prerequisite check, PR-reference verification (`Closes #<N>` lookup), evidence collection (Playwright support or user-supplied), commit-to-PR-branch flow under `docs/evidence/issue-<N>/`, PR description update with inline image references, optional closing comment on the issue, summary output
- [ ] 4.4 Add a guardrail to `dobby-gh-close-issue` that stops with a clear message when no open PR references the target issue
- [ ] 4.5 Add a guardrail to `dobby-gh-close-issue` that warns when the working tree has unrelated uncommitted changes and asks whether to proceed
- [ ] 4.6 Add a guardrail to `dobby-gh-close-issue` that pushes the PR branch before updating the PR description, so embedded image URLs resolve
- [ ] 4.7 Create `skills/dobby-gh-propose-from-issue/SKILL.md` covering: prerequisite check (`gh`, `openspec`), issue lookup (number / URL / keywords), change name format `issue-<N>-<slug>`, OpenSpec artifact generation in dependency order seeded from issue content, "Source: GitHub Issue [#N](url)" line in proposal, optional back-link comment on the issue
- [ ] 4.8 Set all three `dobby-gh-*` skills' `description` to begin with "Internal — …. Invoked by dobby-…-pbi after backend resolution."

## 5. Host mirroring and documentation

- [ ] 5.1 Run `python scripts/sync-skills.py` to regenerate `.github/skills/` and `.claude/skills/` from the new canonical sources
- [ ] 5.2 Run `python scripts/check-skill-sync.py` and confirm a clean tree (exit 0, no drift)
- [ ] 5.3 Update `CLAUDE.md` "What this repository is" and "Architecture" sections to describe the dispatcher + backend-skill pattern and the new `.dobby/config.json` shape
- [ ] 5.4 Update `CLAUDE.md` "Cross-skill invariants" to note: dispatchers never call backend APIs; backend skills own their connection-detail collection; GitHub close requires a PR
- [ ] 5.5 Update the skill layout table in `CLAUDE.md` to list all 9 skills with their canonical paths
- [ ] 5.6 Add a short "Migrating from azdo-defaults.json" subsection to `CLAUDE.md` pointing at `scripts/migrate-dobby-config.py`

## 6. Smoke testing

- [ ] 6.1 In this repo (ADO-backed), run the migration script and confirm `.dobby/config.json` is produced with `backend: "ado"` and the existing org/project/team in the `ado` block
- [ ] 6.2 Invoke `dobby-close-pbi` by intent ("close this") in Claude Code and confirm the dispatcher routes to `dobby-ado-close-pbi` and the flow behaves identically to today
- [ ] 6.3 Invoke `dobby-close-pbi` by intent in Copilot CLI and confirm the same routing and behavior
- [ ] 6.4 Invoke `/dobby-close-pbi` explicitly in Claude Code and confirm the dispatcher fires (not a backend skill directly)
- [ ] 6.5 In a throwaway test directory, create a `.dobby/config.json` with `backend: "github"` and a test repo, invoke `dobby-create-pbi`, and verify the dispatcher routes to `dobby-gh-create-issue`
- [ ] 6.6 In the same test directory, invoke `dobby-close-pbi` for an issue that has no open PR and confirm the skill stops with the expected error message
- [ ] 6.7 In the same test directory, open a PR with `Closes #<N>`, invoke `dobby-close-pbi`, and verify screenshots are committed under `docs/evidence/issue-<N>/` and embedded in the PR description
- [ ] 6.8 Confirm the LLM skill picker does not misroute "close this pbi" to a `dobby-ado-*` or `dobby-gh-*` skill directly when the dispatcher exists; iterate descriptions if needed

## 7. Archival readiness

- [ ] 7.1 Run `openspec status --change dobby-multi-backend --json` and confirm all artifacts report `done`
- [ ] 7.2 Run `openspec validate dobby-multi-backend` (if available) and resolve any reported issues
- [ ] 7.3 Update this `tasks.md` checking off each completed task in commits as work progresses
