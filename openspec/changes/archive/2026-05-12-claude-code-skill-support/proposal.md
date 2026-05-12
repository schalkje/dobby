## Why

The dobby skills (`dobby-create-pbi`, `dobby-close-pbi`, `dobby-propose-from-pbi`, the `openspec-*` workflow skills, and `grill-me`) currently live only under `.github/skills/` — a path discovered by **GitHub Copilot CLI**. The author also works with **Claude Code**, which discovers skills under `.claude/skills/`. Today, running a dobby skill from Claude Code requires symlinking or copy-pasting by hand, which drifts out of sync.

We want one canonical source of skill content, and both hosts to be able to discover it while working on dobby itself.

## What Changes

- Make `skills/<skill-name>/` the **single source of truth** for every skill (SKILL.md, helper scripts, templates).
- Provide copies at `.github/skills/<skill-name>/` and `.claude/skills/<skill-name>/` so that GitHub Copilot CLI and Claude Code can each discover the skills when developing in this repository. These copies are **not leading code** — they exist for in-repo discovery only and are kept in sync from the canonical source.
- Provide a small sync script (`scripts/sync-skills.py`) that copies `skills/` → `.github/skills/` and `skills/` → `.claude/skills/`, plus a check script (`scripts/check-skill-sync.py`) that fails if either copy is out of date.
- Update `README.md` to describe **every** skill, not just `dobby-create-pbi` — its purpose, prerequisites, hosts, and a usage example.
- Update `CLAUDE.md` and `.github/copilot-instructions.md` to point at `skills/` as the source of truth and document the sync rule.

## Capabilities

### New Capabilities
- `multi-host-skills`: Defines the one-source-many-copies layout that makes every skill discoverable from both Copilot CLI and Claude Code, the sync rule, and the documentation contract (README catalog, host-instruction files).

### Modified Capabilities
<!-- None. Existing pbi-creation, closing-evidence, and before-capture specs describe behavior independent of which host invokes the skill; they do not change. -->

## Impact

- **New top-level directory**: `skills/<name>/` becomes the canonical location for every skill.
- **`.github/skills/` and `.claude/skills/`** hold copies for in-repo host discovery only — never edited directly.
- **Helper scripts and templates** live under `skills/<name>/scripts/` and `skills/<name>/templates/` — referenced by their canonical path from the SKILL.md body. Both host copies reference the same paths after sync, so the scripts run from one physical location.
- **New scripts**: `scripts/sync-skills.py` and `scripts/check-skill-sync.py`. Python stdlib only — no new dependencies.
- **Updated docs**: `README.md` (full skill catalog), `CLAUDE.md` and `.github/copilot-instructions.md` (skill layout + sync rule).
- **No new runtime dependencies**.
- **No change to the Azure DevOps integration surface** — `az` CLI, helper scripts, evidence storage, and `openspec` CLI invocations are unchanged.
- **Copilot users** see no behavior change beyond updated helper-script paths (internal, not a user-facing contract).
- **Claude Code users** gain access to every dobby skill without manual setup.
- **Host-specific tuning** is allowed only when actually needed and is handled per-skill by hand (e.g., a sentence noting "use the AskUserQuestion tool — in Claude Code this is the AskUserQuestion built-in"). No generator or templating layer is introduced; if real divergence ever forces a fork, we revisit then.
