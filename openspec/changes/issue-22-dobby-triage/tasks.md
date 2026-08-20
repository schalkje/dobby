# Tasks

## 1. Skill sources

- [x] 1.1 Author `skills/github/dobby-triage/SKILL.md` (gh CLI listing, filters, table, next-action handoff, read-only guardrails + rationalization table)
- [x] 1.2 Author `skills/ado/dobby-triage/SKILL.md` (WIQL listing, same structure, ADO fragments)
- [x] 1.3 Trigger-phrase descriptions on both ("triage", "list issues", "what's open", "show the backlog", "what should I work on")

## 2. Assembly

- [x] 2.1 Add `dobby-triage` to `skills/manifest.json`: `userFacingSkills`, `scenarios.github` (source), `scenarios.ado` (source), `scenarios.combined` (reuse ado)
- [x] 2.2 Regenerate (`build-skills.py dev`) and verify `build` for all three scenarios

## 3. Evals

- [x] 3.1 `skills/github/dobby-triage/evals/evals.json`: ≥3 evals incl. a pressure eval on the read-only rule, plus should/should-not trigger prompts
- [x] 3.2 `run-skill-evals.py --validate` passes

## 4. Docs

- [x] 4.1 Update the user-facing skill list in `CLAUDE.md` (and `scripts/README.md` if it names the set)

## 5. Verification

- [x] 5.1 `build-skills.py build` lint-clean for all scenarios; `check-skill-sync.py` passes; generated SKILL.md ≤500 lines
