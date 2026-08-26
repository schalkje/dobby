# Tasks

> Source: GitHub Issue [#30](https://github.com/schalkje/dobby/issues/30) — "Implement DORA for DevOps risk assessment and test evidence in the ADO skills"
> Spec: `docs/dora-for-devops.md` (§2–§13), with the overrides stated in the issue body.

## 1. Helper script (single source of truth)

- [x] 1.1 `skills/_lib/azdo-dora.py` — questionnaire table, scores, Q4→Q5 skip, 10–104 thresholds, test catalogue with minimum profiles, effective-status derivation, completeness rules
- [x] 1.2 Subcommands: `catalog`, `score`, `read`, `check`, `write-assessment`, `write-evidence`, `finalize`
- [x] 1.3 `_lib` conventions: stdlib only, `AZURE_DEVOPS_EXT_PAT` → `ADO_TOKEN` → `az account get-access-token`, retry/backoff on 429/502/503/504
- [x] 1.4 Guardrails in code: never write legacy `Custom.DORA*`; never emit an `OptedOut` unless user-stated; write Evidence only for `Required`/`OptedIn`, Motivation only for `OptedIn`/`OptedOut`, Status for all twelve; recompute (never trust) `DoraEvidenceComplete` / `DoraClosureAllowed`; `finalize` requires an attestor and refuses on incomplete evidence

## 2. Shared prose fragments

- [x] 2.1 `skills/_fragments/dora-refinement-phase.md` — scope decision, implicit knockouts, prefilled Q1–Q8 with `assumption` marking, arithmetic, test set, mandatory assessment comment, field writes
- [x] 2.2 `skills/_fragments/dora-closure-phase.md` — assessment/staleness checks, evidence harvest, gap reporting, opt-out discipline, recompute gate, attestation, then Done
- [x] 2.3 `skills/_fragments/dora-scope-tag.md` — `Change` tag scope touchpoint for creation
- [x] 2.4 `skills/_fragments/dora-banner.md` — AI-draft banner + source `System.Rev`

## 3. Skill sources

- [x] 3.1 `skills/ado/dobby-update-pbi` — new phase R6a between R5 and R7 (refinement fragment)
- [x] 3.2 `skills/ado/dobby-close-pbi` — new step 7a between steps 4–8, before the Done transition (closure fragment)
- [x] 3.3 `skills/combined/dobby-close-pbi` — same closure phase on the ADO side, harvesting GitHub PR/pipeline links
- [x] 3.4 `skills/ado/dobby-create-pbi` — scope-decision touchpoint (`Change` tag)
- [x] 3.5 `skills/github/*` and `dobby-implement-pbi` untouched in all scenarios

## 4. Assembly

- [x] 4.1 `skills/manifest.json` — register `azdo-dora.py` (owner `dobby-update-pbi`) on ado `dobby-create-pbi`, `dobby-update-pbi`, `dobby-close-pbi` and combined `dobby-close-pbi`
- [x] 4.2 `build-skills.py build` lint-clean for all three scenarios
- [x] 4.3 `build-skills.py dev` + `check-skill-sync.py` → no drift

## 5. Evals

- [x] 5.1 `skills/ado/dobby-update-pbi/evals/evals.json` — out-of-scope PBI, implicit-Low, `assumption`-marked answer, unknown-never-lowest-score pressure
- [x] 5.2 `skills/ado/dobby-close-pbi/evals/evals.json` — recomputed `EvidenceComplete = false`, stale `true` not trusted, missing evidence must not become an opt-out, opt-out without motivation, closure without attestation must not write
- [x] 5.3 `run-skill-evals.py --validate` passes

## 6. Docs

- [x] 6.1 Correct `docs/dora-for-devops.md` §8/§12 per the issue's overrides (dedicated script, `dobby-implement-pbi` out of scope)
- [x] 6.2 Note the DORA helper in `CLAUDE.md` / `.github/copilot-instructions.md` script tables

## 7. Verification

- [x] 7.1 `python skills/_lib/azdo-dora.py --help` and each subcommand `--help` run clean
- [x] 7.2 Offline self-check of scoring/derivation (`score`, `catalog`) against §5/§6 tables
- [x] 7.3 Full build + sync + eval validation green
