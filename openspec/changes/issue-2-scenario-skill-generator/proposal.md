> Source: GitHub Issue [#2](https://github.com/schalkje/dobby/issues/2) — "Build-time generator for scenario-specific skills (replace runtime dispatcher)"

## Why

Today every workflow skill is a runtime **dispatcher** (`dobby-close-pbi`) that reads `.dobby/config.json` and, at invocation time, hands off to a nested **backend** skill (`dobby-ado-close-pbi` / `dobby-gh-close-issue`). This forces every host to ship every backend, makes the LLM read two `SKILL.md` files per intent, and couples skill selection to a `backend`-key branch. A project only ever targets one scenario — it should consume only flat, specialized skills with no runtime routing and no nested resolution.

## What Changes

- **Add** a build-time CLI assembler (`scripts/build-skills.py`, Python stdlib only, `openspec init`-style) with three output modes:
  - `build` — emit all three scenarios to `build/<scenario>/` (inspection/CI). `build/` is gitignored.
  - `init` — scaffold a chosen scenario into a *target project's* `.claude/skills/` + `.github/skills/`.
  - `dev` / self-install — assemble the **github** scenario into **dobby's own** `.claude/skills/` + `.github/skills/` (these copies are committed).
- **Add** a per-scenario source layout under `skills/`: `_lib/` (shared scripts, bundled once when used), `_common/` (scenario-independent skills, copied into every scenario), `ado/`, `github/`, `combined/` (scenario-specialized prose under user-facing names).
- **Add** a per-scenario **manifest** declaring, for each user-facing skill, which folder's file + which `_lib` scripts assemble it. Reuse is explicit: `combined` reuses `ado` for create/update/propose, reuses `github`+ADO-link for implement, and hand-authors only `close`.
- **BREAKING** — **Remove** the runtime dispatcher architecture: `dobby-create-pbi`, `dobby-close-pbi`, `dobby-propose-from-pbi`, `dobby-update-pbi` cease to be routing skills, and backend-named skills (`dobby-ado-*`, `dobby-gh-*`) are retired as *shipped* skills — they become scenario source files under the user-facing names.
- **Replace** `scripts/sync-skills.py` (blind mirror of every skill) with the generator's `dev` mode; reconcile `scripts/check-skill-sync.py` to validate the generated github-scenario tree.
- **Demote** the `.dobby/config.json` `backend` key: it is **retained** (records which scenario the project was generated with) but no longer read at invocation to route. Connection blocks (`ado`/`github`) stay per-project.
- **Update** `CLAUDE.md` and `scripts/README.md` to describe the generator and source layout.

## Capabilities

### New Capabilities
- `scenario-skill-generation`: A build-time CLI that assembles flat, scenario-specialized skill sets from a per-scenario source layout + manifest, in `build`/`init`/`dev` modes, with `_lib` scripts bundled once and no template/conditional syntax in output.

### Modified Capabilities
- `backend-routing`: The `backend` key is demoted from a runtime router to a generation-time record; dispatcher skills and runtime nested-skill resolution are removed.
- `multi-host-skills`: `sync-skills.py`'s "mirror every skill" model is replaced by the generator's `dev` mode (github scenario → dobby's own committed host copies); `check-skill-sync.py` validates the generated tree.

## Impact

- **New**: `scripts/build-skills.py`; `skills/_lib/`, `skills/_common/`, `skills/ado/`, `skills/github/`, `skills/combined/`; per-scenario manifest file(s); `build/` (gitignored).
- **Migrated**: existing `skills/dobby-ado-*`, `skills/dobby-gh-*`, dispatcher skills → reorganized into the new source tiers under user-facing names.
- **Removed/replaced**: `scripts/sync-skills.py`; reworked `scripts/check-skill-sync.py`.
- **Docs**: `CLAUDE.md`, `scripts/README.md`.
- **Config**: `.dobby/config.json` schema note (backend demoted, retained).
- **No behavior change** to the work-item lifecycle itself — packaging/architecture only.
