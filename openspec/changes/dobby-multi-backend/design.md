## Context

Today, the three dobby workflow skills (`dobby-create-pbi`, `dobby-close-pbi`, `dobby-propose-from-pbi`) speak only Azure DevOps. They embed `az boards` invocations, ADO-specific REST helper scripts, and field semantics (System.Description, Microsoft.VSTS.Common.AcceptanceCriteria, AreaPath, IterationPath) directly in the SKILL.md prose. Project tracker connection details live in `.dobby/azdo-defaults.json`, whose filename and schema both presuppose ADO.

We need the same conversational entry points to work for projects that track issues in GitHub. The user has confirmed (during the explore phase that produced this proposal) that "PBI" and "issue" can be treated as interchangeable concepts and that the project itself decides which backend is in play. A single project targets exactly one tracker — no mixing.

This sits alongside the existing host-axis abstraction (canonical `skills/` mirrored into `.claude/skills/` and `.github/skills/` for Claude Code and Copilot CLI discovery) and uses an analogous separation: one canonical author surface, multiple downstream targets selected by configuration.

## Goals / Non-Goals

**Goals:**

- A user typing "close this pbi", "close this", or `/dobby-close-pbi` gets routed automatically to the right tracker without thinking about the backend.
- Adding a new backend in the future (e.g., Jira, Linear) is a matter of writing three new backend skills plus one config block — no edits to dispatchers or existing backend skills.
- Each backend implementation is single-purpose and free of `if backend == ...` branches. Reading `dobby-gh-close-issue` shows only the GitHub flow.
- User vocabulary (the existing skill names) survives unchanged. Muscle memory is preserved.
- Migration of existing checkouts from `.dobby/azdo-defaults.json` to `.dobby/config.json` is automatic, idempotent, and reversible (the migration script never destroys data).
- The pattern works identically under Claude Code and Copilot CLI without host-specific tricks.

**Non-Goals:**

- Multi-tracker projects (one project, one backend).
- Per-invocation backend overrides (`--backend github` flags, "close this in github" natural-language hints). Out of scope; revisit only if it becomes a real need.
- Symmetric feature parity between ADO and GitHub. Where the trackers genuinely differ — attachments, hierarchy, iteration/area paths — each backend skill follows its host's idiomatic flow rather than forcing a lowest-common-denominator abstraction.
- Migration of historical work items between trackers.
- A unified Python "backend" library that abstracts over `az` and `gh` APIs. The skills remain prompt-driven; backend logic stays visible in the SKILL.md prose.

## Decisions

### Decision 1: Single `.dobby/config.json` file with a top-level `backend` selector

The config is one JSON file with the shape:

```jsonc
{
  "backend": "ado",                       // or "github"
  "ado":    { "organization": "...", "project": "...", "team": "...", "devLinks": { ... } },
  "github": { "owner": "...", "repo": "...", "defaultLabels": [...], "projectNumber": 7 }
}
```

Only the active backend's block is required to be populated; the other may be omitted entirely.

**Alternatives considered:**

- *Per-backend files* (`.dobby/ado.json`, `.dobby/github.json`, plus a small `.dobby/project.json` for the selector). Lower-friction migration (rename `azdo-defaults.json` → `ado.json`) but more files to load and a more diffuse mental model.
- *Keep `azdo-defaults.json`, add a sibling `github-defaults.json`, and infer backend from which one exists.* Magical and fragile — what if both exist?

**Why the single-file choice wins:** one read, one source of truth, no inference. The schema is self-documenting: a developer opening the file sees both the selector and the per-backend shape at a glance.

### Decision 2: Three dispatcher skills + six backend skills

The three existing skill names become **dispatchers** whose only job is reading the config and handing off:

```
skills/
├── dobby-create-pbi/              ← dispatcher (preserves user vocabulary)
├── dobby-close-pbi/               ← dispatcher
├── dobby-propose-from-pbi/        ← dispatcher
├── dobby-ado-create-pbi/          ← ADO impl (extracted from current dobby-create-pbi)
├── dobby-ado-close-pbi/           ← ADO impl (extracted)
├── dobby-ado-propose-from-pbi/    ← ADO impl (extracted)
├── dobby-gh-create-issue/         ← new
├── dobby-gh-close-issue/          ← new
└── dobby-gh-propose-from-issue/   ← new
```

Each dispatcher is ~30 lines: read `.dobby/config.json` → prompt for `backend` if missing → write it back → `Read` the matching backend SKILL.md → follow its instructions as if invoked directly.

**Alternatives considered:**

- *Inline branching inside each existing skill* (`if backend == ado: ... else: ...`). Keeps the file count down but produces long, forky SKILL.md files where reading-flow is hard to follow. The user explicitly said "I don't mind more skills" — this is the cleaner option for them.
- *No dispatcher; rely on vocabulary* (`dobby-create-pbi` for ADO, `dobby-create-issue` for GitHub, user picks the right name). Breaks the user's expressed preference for interchangeable vocabulary and routing-by-config.

**Why the dispatcher pattern wins:** preserves the names the user types, isolates per-backend logic into single-purpose skills, and adds a new backend in the future without touching existing files.

### Decision 3: Dispatch via `Read` + follow, not via skill-tool invocation

The dispatcher does **not** invoke the backend skill through its host's Skill tool. It uses the `Read` tool to load `skills/dobby-<backend>-<workflow>/SKILL.md` and then follows the instructions found there. The user's original input is treated as the input to that downstream skill.

**Alternatives considered:**

- *Use the host's Skill tool to invoke the backend skill.* Available in Claude Code (the `Skill` tool); behavior in Copilot CLI is less certain. Skill-from-skill invocation is also not a guaranteed primitive across hosts.

**Why Read-and-follow wins:** it's just file IO + instruction-following. Works identically on every host that runs prompt-driven skills, because it uses no host-specific primitives.

### Decision 4: Skill-picker disambiguation via description discipline

To prevent the LLM from picking a backend-specific skill directly when the user types "close this pbi", the description fields are written so the dispatcher wins:

```yaml
# dobby-close-pbi (dispatcher)
description: Close an issue/PBI in this project's tracker. Auto-detects
  Azure DevOps vs GitHub from .dobby/config.json. Use this for any
  "close this", "close this pbi", or "close this issue" request.

# dobby-ado-close-pbi (implementation)
description: Internal — closes a PBI in Azure DevOps. Invoked by
  dobby-close-pbi after backend resolution. Do not invoke directly
  unless forcing the ADO backend.
```

The "Internal — invoked by" framing steers the picker away from the backend skills for casual intent while keeping them available for explicit invocation.

**Risk acknowledged:** picker behavior is heuristic, not deterministic. Mitigation: prototype the `close` workflow end-to-end in both hosts with both backend settings before duplicating the pattern to `create` and `propose-from`.

### Decision 5: Backend connection details collected lazily by the backend skill, not the dispatcher

The dispatcher only resolves the `backend` selector. It does **not** collect `organization`, `project`, `team`, `owner`, `repo`, etc. Those are gathered by the backend skill on its first run, written into the corresponding block of `.dobby/config.json`, and reused thereafter.

**Why:** keeps the dispatcher minimal and oblivious to backend-specific fields. Each backend skill already needs to know its own connection details — having it own that collection produces less duplication and clearer separation than threading details through the dispatcher.

### Decision 6: GitHub close-issue uses the PR as the evidence vehicle and requires a PR

In GitHub's idiomatic workflow, an issue is closed by a PR with a `Closes #<N>` directive. `dobby-gh-close-issue` leans into that:

1. Verifies an open PR references the issue (via `Closes #<N>`, `Fixes #<N>`, or `Resolves #<N>` in the PR body, or via a linked-issue relationship). If none → stop with a clear error: "No PR references issue #<N>. Create one first."
2. Runs Playwright (or accepts user-supplied screenshots) and writes PNGs to `docs/evidence/issue-<N>/{before,after}-*.png` on the PR branch.
3. `git add` + commit + push those files.
4. Updates the PR description to embed the screenshots inline (relative paths render via `raw.githubusercontent.com`) and ensures it includes `Closes #<N>`.
5. Optionally adds a closing comment on the issue itself summarizing the PR and linking to it.
6. Issue closure happens naturally when the PR merges — the skill does not call `gh issue close`.

**Alternatives considered:**

- *Commit screenshots, but close the issue directly with `gh issue close` regardless of PR state.* Loses the auto-close-on-merge guarantee and decouples the closure from the work that produced it.
- *Use GitHub Actions artifacts.* Requires a workflow file in the repo and has retention windows. Heavier infrastructure than this skill should impose.
- *Use the `user-images.githubusercontent.com` CDN like a human drag-dropping in the browser.* No public API; only the web UI's private endpoint works, and it's undocumented and brittle.
- *Skip image embedding entirely; link to local `.dobby/evidence/` paths.* Reviewers can't see the evidence without a clone.

**Why PR-as-vehicle wins:** matches GitHub's native flow, ships visual evidence into the review where reviewers actually see it, and produces durable URLs after merge. The "binary in git" cost is bounded: scoped directory, small files, easy to prune later.

**Asymmetry acknowledged:** the ADO closure flow updates the work item directly and is PR-agnostic. The GitHub flow requires a PR. This is by design — each backend follows its native idiom rather than forcing the trackers to look symmetric.

### Decision 7: Migration is a one-shot Python script

`scripts/migrate-dobby-config.py` is invoked manually (or automatically by any dispatcher on first run if it sees `.dobby/azdo-defaults.json` and no `.dobby/config.json`). Behaviour:

1. If `.dobby/config.json` already exists → no-op.
2. If `.dobby/azdo-defaults.json` exists → load it, wrap its content in `{ "backend": "ado", "ado": { ... } }`, write `.dobby/config.json`.
3. Remove `.dobby/azdo-defaults.json` only after `.dobby/config.json` is written successfully.
4. Idempotent — safe to re-run; refuses to overwrite an existing `config.json`.

CLI flags: `--dry-run` (print the resulting config without writing), `--force` (allow overwrite — not enabled by default).

## Risks / Trade-offs

- **[Skill-picker misroutes "close this" to a backend skill directly]** → Mitigation: discipline in description fields (Decision 4); prototype `close` flow first and iterate descriptions until routing is stable in both hosts.
- **[`raw.githubusercontent.com` URLs in PR description break when branch is deleted before merge]** → Mitigation: the skill ensures the branch is pushed and the PR is open before generating URLs; after merge, the files live in main and URLs continue to resolve.
- **[Binary files (PNGs) in main git history bloat repo size over time]** → Mitigation: scoped to `docs/evidence/issue-<N>/`, easy to prune with a periodic `git rm -r docs/evidence/issue-<closed-N>/` housekeeping commit. Documented but not enforced by the skill.
- **[GitHub close-issue requires a PR, which is a new workflow constraint for users coming from the ADO flow]** → Mitigation: clear error message points to the obvious fix; the constraint matches GitHub norms so most users will already be operating this way.
- **[Existing checkouts of dobby projects break when the dispatcher cannot find `.dobby/config.json`]** → Mitigation: dispatcher detects `.dobby/azdo-defaults.json` and runs migration automatically on first invocation; never wipes data.
- **[Two trees of host-mirrored skill copies now hold 9 skills instead of 5, increasing the surface for sync drift]** → Mitigation: `check-skill-sync.py` already catches drift; CI/pre-commit invocation recommended in `CLAUDE.md`.

## Migration Plan

1. Land the proposal, design, and specs in this change directory.
2. Implement `scripts/migrate-dobby-config.py` and verify it on a copy of the current `.dobby/azdo-defaults.json` in this repo.
3. Author the three dispatcher SKILL.md files (replacing today's content).
4. Move today's ADO skill bodies into `dobby-ado-*` siblings (mechanical copy + path update for helper scripts).
5. Author the three `dobby-gh-*` skills.
6. Run `python scripts/sync-skills.py` and confirm `check-skill-sync.py` passes.
7. Update `CLAUDE.md` to describe the new architecture, the config file, and the GitHub flow's PR requirement.
8. Smoke-test the `close` workflow end-to-end on both backends in both hosts before considering the change ready to archive.

**Rollback strategy:** the change is additive at the skill layer. To revert: restore the previous SKILL.md contents in `dobby-{create,close,propose-from}-pbi`, delete the six new skill directories, rename `.dobby/config.json` back to `.dobby/azdo-defaults.json` (extracting the `ado` block), re-sync. The migration script's `--dry-run` mode and idempotency make this straightforward.
