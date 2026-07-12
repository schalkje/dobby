## Context

Dobby ships its workflow skills as **dispatcher + backend** pairs. A user intent ("close this pbi") resolves to a dispatcher skill (`dobby-close-pbi`) that, at runtime, reads `.dobby/config.json` → `backend` and `Read`s a nested backend `SKILL.md` (`dobby-ado-close-pbi` or `dobby-gh-close-issue`). Consequences:

- Every host copy ships **all** backends even though a project targets exactly one scenario.
- The LLM reads two `SKILL.md` files per intent (dispatcher, then backend) and must execute a `backend`-key branch correctly every time.
- Skill descriptions must be tuned to keep the dispatcher the "preferred match" and backends "internal" so the picker doesn't collide.

Today, code is shared **by reference**: `azdo-update-fields.py` physically lives in one skill folder but is referenced by four SKILL.md files. Host copies are produced by `scripts/sync-skills.py`, which blindly mirrors *every* canonical skill into `.claude/skills/` and `.github/skills/`.

This change moves scenario selection from **invocation time** to **build time**: a CLI assembles a flat, scenario-specialized skill set per project. Constraints: Python **stdlib only** (consistent with existing repo scripts); **no templating engine** — generated SKILL.md files are prompts an LLM reads, so source files must read as-written (readability beats DRY).

## Goals / Non-Goals

**Goals:**
- A single CLI (`scripts/build-skills.py`) with `build`, `init`, and `dev` modes.
- A three-tier source layout (`_lib`, `_common`, scenario folders) + a per-scenario manifest that makes reuse explicit.
- Flat output under user-facing names (`dobby-create-pbi`, `dobby-close-pbi`, …) with **no** dispatcher, **no** runtime `backend` branch, **no** template/conditional syntax.
- `_lib` scripts bundled **once** per scenario (preserve shared-by-reference, not forked copies).
- `combined` stays minimal: reuse `ado` for create/update/propose, `github`+ADO-link-step for implement, hand-author only `close`.
- Retire `sync-skills.py`; reconcile `check-skill-sync.py` with the generated tree.

**Non-Goals:**
- New scenarios beyond the three (the full repo×tracker matrix). The manifest stays extensible; only three ship.
- Any change to work-item lifecycle *behavior* — this is architecture/packaging only.
- A templating/macro language. Specialized prose is hand-authored per scenario.

## Decisions

### D1. Build-time assembly over runtime dispatch
Replace the dispatcher entirely rather than keep it as a fallback. A project's scenario is fixed at generation; shipping the other backends or re-deciding at every invocation is pure overhead.
- *Alternative considered:* keep dispatchers but pre-resolve. Rejected — leaves nested reads and `backend` branching in shipped skills, defeating the point.

### D2. Source layout: three tiers of building block
```
skills/
  _lib/        shared scripts: azdo-update-fields.py, azdo-add-comment.py,
               azdo-upload-attachment.py, azdo-add-dev-links.py, evidence-store.py
  _common/     scenario-independent skills: openspec-*, grill-*, dobby-worktree
  ado/         dobby-{create,update,propose,close,implement}-pbi (ADO prose)
  github/      dobby-{create,update,propose,close,implement}-pbi (GitHub prose)
  combined/    ONLY skills that genuinely span both backends (close)
```
A skill's SKILL.md lives in exactly one scenario folder (or `_common`). `combined` holds only hand-authored spanning files; everything else it needs is declared as a reuse of `ado`/`github` in the manifest.
- *Alternative considered:* one folder per (skill × backend) flat. Rejected — obscures which files are shared vs specialized and bloats `combined`.

### D3. Per-scenario manifest declares assembly
A declarative manifest (JSON, stdlib-parseable) maps, per scenario, each **user-facing skill name** → `{ source: <folder>/<skill>, scripts: [<_lib names>] }`. The `combined` manifest expresses reuse by pointing `create-pbi`/`update-pbi`/`propose-from-pbi` at `ado/…`, `implement-pbi` at `github/…` **plus** an ADO link step, and `close-pbi` at `combined/…`.
- *Alternative considered:* infer reuse from folder presence. Rejected — implicit; the issue explicitly wants reuse to be *explicit*.

### D4. `implement-pbi` in combined = github file + ADO link step, woven at a named source anchor
Rather than fork the whole github `implement-pbi`, the combined manifest entry references the github source and **weaves** a thin, named "connect to ADO and link the PBI to the PR (`azdo-add-dev-links.py`)" fragment into it. Mechanism (resolved during grilling): the **github** `implement-pbi` source carries a named anchor comment (e.g. `<!-- dobby:combined-seam:link-pbi-to-pr -->`) at the correct lifecycle point — immediately after PR creation (Phase 9c), **not** end-of-file. The generator, **for the combined scenario only**, replaces that anchor with the fragment from `combined/`; for the `ado` and `github` scenarios it **strips the anchor**. The anchor never survives into output, so "no template/conditional syntax in output" holds — the seam is a source-level construct removed during assembly, and the ADO step lands semantically placed rather than dangling after the Summary.
- *Alternative considered:* plain end-of-file concatenation. Rejected — the ADO link step belongs after PR creation, not after "Done"; appending at EOF reads as dangling.
- *Alternative considered:* duplicate the github implement file into `combined/`. Rejected — violates "preserve reuse, don't fork."

### D9. Generated output is lint-gated inside the assembler
The assembler SHALL run a forbidden-pattern lint over every emitted `SKILL.md` **after** anchor stripping and **fail the build** if any appear: nested-skill `Read … SKILL.md` backend routing, `backend`-value branching for routing, template/conditional/macro markers, or a leftover combined-seam anchor. This makes the "flat, no-template" acceptance criteria self-enforcing on every `build`/`init`/`dev` run rather than unverified prose.
- *Alternative considered:* a separate CI-only test. Rejected — local `build`/`dev` runs could emit bad output with no immediate feedback.

### D5. `_lib` scripts bundled once per scenario
When the manifest says a scenario's skills reference `_lib/azdo-update-fields.py`, the generator copies it to a single shared location in the output scenario (e.g. `<scenario>/_lib/` or the owning skill's `scripts/`) and the generated SKILL.md prose references that one path — never duplicated per referencing skill. The generator de-duplicates by script name.

### D6. Three output modes, one assembler core
- `build` → `build/<scenario>/` for all three scenarios (CI/inspection). `build/` gitignored.
- `init <target> <scenario>` → writes the scenario's `.claude/skills/` + `.github/skills/` into a target project.
- `dev` → assembles the **github** scenario into dobby's *own* `.claude/skills/` + `.github/skills/`; these are committed. Replaces `sync-skills.py`.
All three call the same assembler; modes differ only in destination + which scenario(s).

### D7. `backend` key retained but demoted
`.dobby/config.json` keeps `backend` and the connection blocks. `backend` becomes a generation-time record ("this project was generated for github"), not read at invocation. No migration of existing config values needed.

### D8. Generated host copies still carry the "do not edit" notice
Generated SKILL.md files keep a notice pointing back at the scenario source (`skills/<scenario>/<skill>/SKILL.md`), preserving the multi-host-skills "copies declare themselves as copies" invariant.

## Risks / Trade-offs

- **Drift between three hand-authored scenario prose sets** → Mitigation: `_common` + `_lib` carry everything genuinely shared; only intentionally-divergent prose is per-scenario. `combined` reuses rather than forks.
- **Generated tree diverges from committed dobby host copies** → Mitigation: reworked `check-skill-sync.py` runs the generator's `dev` assembly into a temp dir and diffs against the committed `.claude/`/`.github/` trees; CI fails on drift, exact fix command printed.
- **Losing shared-by-reference for `_lib`** → Mitigation: D5 de-dupes by script name; a manifest/assembler test asserts each `_lib` script appears once per scenario.
- **`combined` append-fragment (D4) reintroduces hidden coupling** → Mitigation: the fragment is a named, readable prose file under `combined/`; concatenation order is explicit in the manifest; generated output is plain prose (verifiable by the "no template syntax" check).
- **Existing muscle memory / intents** (`dobby-close-pbi` etc.) must still resolve → Mitigation: user-facing skill names are preserved exactly; only the *implementation* behind them changes.

## Migration Plan

1. Land source layout (`_lib`, `_common`, `ado`, `github`, `combined`) by moving existing skill bodies into tiers under user-facing names (no behavior change to prose yet).
2. Add the per-scenario manifest(s) + `scripts/build-skills.py` (assembler core + three modes).
3. Run `dev` mode to regenerate dobby's own `.claude/`/`.github/` from the **github** scenario; commit.
4. Rework `check-skill-sync.py`; remove `sync-skills.py`; gitignore `build/`.
5. Update `CLAUDE.md` + `scripts/README.md`.
6. Rollback: the old dispatcher skills remain in git history; revert the commit to restore runtime dispatch. No data/state migration is involved (config `backend` values are untouched).

## Resolved Questions (grilling, 2026-06-24)

- **Manifest shape** → **single `skills/manifest.json`** with a `scenarios` map, so cross-scenario reuse (`combined` reuses `ado`/`github`) is visible at a glance.
- **`_lib` bundling location in output** → **the owner skill's `scripts/` dir** (one designated owner per script; others reference that path), keeping generated path references identical to today's `skills/<name>/scripts/<script>.py` shape. De-dupe by script name.
- **Source gaps (discovered during grilling)** → there is **no `dobby-gh-update-issue`** today and the current `dobby-implement-pbi` is **ADO-centric**. Both github sources are **authored new** in this change: a new `github/dobby-update-issue` and a github-flavored `github/dobby-implement-pbi`; the existing implement-pbi becomes the `ado` source.
- **Combined `implement-pbi` seam** → named source anchor stripped in output (see D4).
- **Output enforcement** → forbidden-pattern lint inside the assembler (see D9).
- **Cutover** → clean cut in one PR, `git mv` for 1:1 relocations to preserve history, `check-skill-sync.py` rework lands in the same commit as the regenerated copies. User-facing names preserved → no consumer break.
- **Placement** → `dobby-worktree`, `openspec-*`, `grill-*` → `_common`; the five work-item skills (`create/update/propose/close/implement`) → scenario folders. `evidence-store.py` (currently not referenced by any SKILL.md prose) is bundled with the `ado` `close-pbi` and flagged for review rather than deleted.
