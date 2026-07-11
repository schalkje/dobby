## 1. Source layout migration

- [x] 1.1 Create the three-tier skeleton: `skills/_lib/`, `skills/_common/`, `skills/ado/`, `skills/github/`, `skills/combined/`
- [x] 1.2 Move shared helper scripts into `skills/_lib/` (`azdo-update-fields.py`, `azdo-add-comment.py`, `azdo-upload-attachment.py`, `azdo-add-dev-links.py`, `evidence-store.py`)
- [x] 1.3 Move scenario-independent skills into `skills/_common/` (`openspec-*`, `grill-*`, `dobby-worktree`)
- [x] 1.4 Move ADO-specialized prose into `skills/ado/` under user-facing names (`dobby-{create,update,propose,close,implement}-pbi`), updating `_lib` script path references
- [x] 1.5 Move GitHub-specialized prose into `skills/github/` under user-facing names, updating script path references
- [x] 1.6 Author NEW `github/dobby-update-issue` source (no `dobby-gh-update-issue` exists today)
- [x] 1.7 Author NEW github-flavored `github/dobby-implement-pbi` (existing ADO-centric implement-pbi becomes the `ado` source); add the `<!-- dobby:combined-seam:link-pbi-to-pr -->` anchor right after PR creation (Phase 9c)
- [x] 1.8 Author the `combined`-specific `close-pbi` source under `skills/combined/`
- [x] 1.9 Author the `combined` ADO-link fragment (the `azdo-add-dev-links.py` PBI→PR step) that the generator substitutes for the seam anchor
- [x] 1.10 Decide `evidence-store.py`: bundle with `ado/dobby-close-pbi` scripts and flag for review (not referenced by any SKILL.md prose today)

## 2. Manifest

- [x] 2.1 Define the per-scenario manifest schema (user-facing skill → source folder/file + `_lib` scripts)
- [x] 2.2 Write the `ado` scenario manifest entries
- [x] 2.3 Write the `github` scenario manifest entries
- [x] 2.4 Write the `combined` scenario manifest: reuse `ado` for create/update/propose, `github`+link-step for implement, `combined` for close
- [x] 2.5 Document the manifest schema (in `scripts/README.md`)

## 3. Assembler core (`scripts/build-skills.py`)

- [x] 3.1 Implement the assembler core: read manifest, resolve sources per scenario, copy `_common` into every scenario
- [x] 3.2 Assemble each user-facing skill from its manifest source; prepend the "generated — do not edit, source is skills/<scenario>/<skill>" notice
- [x] 3.3 Bundle `_lib` scripts once per scenario (de-dupe by name); rewrite generated prose to reference the single bundled path
- [x] 3.4 Implement the `combined` seam: substitute the ADO-link fragment for the `<!-- dobby:combined-seam:* -->` anchor (combined only); strip the anchor for ado/github
- [x] 3.5 Implement the forbidden-pattern lint pass (run after anchor stripping): fail the build on nested-skill backend `Read`, `backend` branching, template/macro syntax, or a leftover seam anchor
- [x] 3.6 Guarantee output is flat (one SKILL.md per user-facing name, no dispatcher, no `backend` branch)

## 4. Output modes

- [x] 4.1 `build` mode → emit all three scenarios to `build/<scenario>/`
- [x] 4.2 `init <target> <scenario>` mode → write the scenario's skills to a target project's `.claude/skills/` + `.github/skills/`
- [x] 4.3 `dev` mode → assemble the **github** scenario into dobby's own `.claude/skills/` + `.github/skills/`
- [x] 4.4 Reject unknown modes with usage output; stdlib-only imports

## 5. Retire old flow

- [x] 5.1 Add `build/` to `.gitignore`
- [x] 5.2 Rework `scripts/check-skill-sync.py` to diff committed host copies against the generator's `dev` (github) assembly, printing the exact fix command
- [x] 5.3 Remove `scripts/sync-skills.py`
- [x] 5.4 Remove the now-retired shipped dispatcher + backend-named skill folders that are superseded by the generated tree

## 6. Regenerate & docs

- [x] 6.1 Run `dev` mode; commit dobby's regenerated `.claude/skills/` + `.github/skills/` (github scenario)
- [x] 6.2 Update `.dobby/config.json` schema note: `backend` retained as a record, not a runtime router
- [x] 6.3 Update `CLAUDE.md` (skill layout, generator, demoted backend key)
- [x] 6.4 Update `scripts/README.md` (source layout, manifest, three modes, check script)

## 7. Verification

- [x] 7.1 Run `build` mode; assert `build/ado|github|combined/` each contain a flat skill set
- [x] 7.2 Assert no generated `SKILL.md` contains dispatcher/nested-read prose, `backend` branching, or template syntax
- [x] 7.3 Assert each `_lib` script appears exactly once per scenario
- [x] 7.4 Run `check-skill-sync.py`; assert exit 0 against the freshly regenerated committed copies
- [x] 7.5 Smoke-test `init` mode into a throwaway target dir; confirm `.claude/skills/` + `.github/skills/` populated
