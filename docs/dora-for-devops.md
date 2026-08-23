# DORA for DevOps — process specification for dobby skills

> **Status:** design input for skill changes. Not itself a policy document.
> **Organization:** internal (name withheld). **Tracker:** Azure DevOps (`ado` and `combined` scenarios).
> **Authoritative policy sources:** the internal DORA-for-DevOps policy document (v1.0) and the internal Change Management Process (v4.2), both titled *valid from 1 September 2026*.
> **Authoritative implementation source:** the internal Azure DevOps DORA PBI risk-assessment extension, v0.2.8 (work-item form group "DORA"), verified against the live organization on 2026-08-21.

This document describes the DORA-for-DevOps per-change process **as it is actually implemented in Azure DevOps**, so that dobby's skills can be updated to:

1. perform the **risk assessment during refinement** (`dobby-update-pbi`, `dobby-create-pbi`, `dobby-propose-from-pbi`), and
2. **register test evidence when closing** a PBI (`dobby-close-pbi`, `dobby-implement-pbi`).

---

## 1. Why this exists

DORA requires a risk assessment and proportionate, evidenced testing for every *significant* IT change. A DevOps sprint contains 10–20 changes, so a full assessment per item is impractical. The adopted approach is a **hybrid**: a fast implicit low-risk path for clearly low-risk changes, and an explicit scored questionnaire for the rest.

The control objective is a defensible chain:

```
change → risk classification → selected tests → execution → evidence → audit trail
```

The **unit of assessment is the PBI**. Not the sprint (too coarse), not the Epic/Feature (too disruptive to the way of working).

---

## 2. Scope: is this PBI a change?

A PBI is in DORA scope when it represents a **significant IT change**. In the Azure DevOps implementation, scope is driven **entirely by the `Change` tag**:

```
Custom.DoraInScope = System.Tags contains "Change"
```

The DORA form group only renders its assessment panels when the tag is present. This was verified against two reference PBIs:

| Reference PBI | Tags | `Custom.DoraInScope` | `Custom.DoraFlowType` | Meaning |
|---|---|---|---|---|
| PBI **A** | *(none)* | `false` | *(unset)* | No change → out of scope, panel hidden |
| PBI **B** | `Change` | `true` | `Implicit` | Change → in scope, DORA panel appears |

**Out of scope examples** (do not tag, do not assess): investigations/spikes, documentation-only work, onboarding colleagues, other non-technical sprint activities, manual data entry, and data updates performed with **unchanged** reusable scripts.

**In scope**: code changes, changed scripts, relevant technical/configuration changes. If a reusable script itself changes, that changed part is in scope.

There is also a `bypass` tag constant (`DORA_BYPASS_TAG = "bypass"`) in the extension. Skills should **read** it but never set it — bypassing is a human governance decision.

### Skill decision rule

A skill must first answer: **does this PBI represent a significant IT change?**

- **No** → explain *why* it is out of scope, do **not** run scoring, and do not add the `Change` tag.
- **Yes** → ensure the `Change` tag is present, then continue to the implicit criteria.
- **Cannot tell from the available text** → say exactly what is missing (does code, script, configuration, authentication, data processing, or runtime behaviour change?). Never classify from the title alone.

---

## 3. Out-of-scope field state

When a PBI is not in scope, the extension writes a neutral, closure-permitting state:

```
Custom.DoraInScope             = false
Custom.DoraClosureAllowed      = true
Custom.DoraFinalRiskClass      = "Low"
Custom.DoraFinalRiskScore      = 0
Custom.DoraSuggestedTestProfile= "Low"
(all question, score, and test fields cleared)
```

This is exactly the state observed on reference PBI **A**. **A skill must not read `FinalRiskClass = Low` as an assessment result without first checking `DoraInScope`.**

---

## 4. Implicit low-risk path

When the PBI is in scope, `Custom.DoraFlowType` defaults to `Implicit`. Choosing (or leaving) the implicit path asserts that **at least one** knockout criterion applies:

| # | Criterion | Meaning |
|---|---|---|
| 1 | **Bronze SLA** | The change concerns a business application with a Bronze SLA, or a component not used by any Silver- or Gold-rated business application. |
| 2 | **Immediate mitigation** | Rollback, roll-forward, or disabling can immediately revert the change without permanent damage — including no already-corrupted database records. |

Resulting field state (extension `implicit-low` branch):

```
Custom.DoraInScope             = true
Custom.DoraFlowType            = "Implicit"
Custom.DoraClosureAllowed      = true
Custom.DoraFinalRiskClass      = "Low"
Custom.DoraFinalRiskScore      = 10          # sentinel, not a computed sum
Custom.DoraSuggestedTestProfile= "Low"
(all Q1–Q8 answers and Q1–Q8 scores cleared)
```

> **"Low by default" ≠ "low without reasoning."** The score `10` is a sentinel the extension writes; it is not evidence of an assessment. The skill must record *which* criterion applies and *where in the PBI* that is substantiated.

**Good skill output**

```
Classification: Low
Basis:
  - Implicit criterion: Bronze SLA
  - Evidence from PBI: "<quoted text or field>"
  - Explicit assessment required: No
```

**Unacceptable skill output**

```
Classification: Low because most changes are low risk.
```

---

## 5. Explicit risk assessment

If neither implicit criterion applies, the user switches the flow to `Explicit` and answers eight questions. The extension's questionnaire — values, labels, and scores — is reproduced verbatim below. **Skills must write the exact `value` strings**; the labels are for display only.

### Q1 — SLA rating (`Custom.DoraQ1SlaRating` → `Custom.DoraQ1Score`)

| Value | Label | Score |
|---|---|---:|
| `silver` | Silver | 10 |
| `gold` | Gold | 20 |

Bronze is absent by design — it routes to the implicit path.

### Q2 — Mitigating measures (`Custom.DoraQ2MitigatingMeasures` → `Custom.DoraQ2Score`)

| Value | Label | Score |
|---|---|---:|
| `withinTwoHoursNoDataCorruptionRisk` | Rollback/roll-forward/feature-flag disabling within 2 hours, no data-corruption risk | 0 |
| `notWithinTwoHoursOrDataCorruptionRisk` | Not within 2 hours, or data-corruption risk | 20 |

The two-hour boundary is marked **indicative** in the policy.

### Q3 — Change impact (`Custom.DoraQ3ChangeImpact` → `Custom.DoraQ3Score`)

| Value | Label | Score |
|---|---|---:|
| `contentOnly` | Content only (text, images, layout, design) | 0 |
| `bugfixOrSmallBusinessLogicChange` | Bugfix or small business-logic change | 5 |
| `mediumBusinessLogicChange` | Medium business-logic change | 10 |
| `largeBusinessLogicOrArchitectureChange` | Large business-logic or architecture change | 15 |

Connecting to a new source system for the first time is the policy's example of *large*. The policy notes that more examples are still needed for *medium*.

### Q4 — New functionality (`Custom.DoraQ4NewFunctionality` → `Custom.DoraQ4Score`)

| Value | Label | Score | Routing |
|---|---|---:|---|
| `no` | No | 0 | Continue with Q5 |
| `yes` | Yes | 3 | **Q5 is skipped** — the extension disables the incident-history control and forces `Q5 = no` |

### Q5 — Incident history (`Custom.DoraQ5IncidentHistory` → `Custom.DoraQ5Score`)

| Value | Label | Score |
|---|---|---:|
| `no` | No | 0 |
| `some` | Some | 3 |
| `many` | Many | 8 |

Only applicable when `Q4 = no`.

### Q6 — Familiarity with the type of change (`Custom.DoraQ6Familiarity` → `Custom.DoraQ6Score`)

| Value | Label | Score |
|---|---|---:|
| `dailyOperationOrFamiliarCode` | Daily operation / familiar code | 0 |
| `unfamiliarProductModuleOrCode` | Unfamiliar product/module/code | 3 |
| `outsideControlThirdPartyOrOtherTeams` | Outside control / 3rd party / other teams | 8 |

Pilot feedback flagged this question as unclear — a skill should explain it rather than just present it.

### Q7 — Authentication and authorization (`Custom.DoraQ7AuthImpact` → `Custom.DoraQ7Score`)

| Value | Label | Score |
|---|---|---:|
| `none` | No | 0 |
| `applicationRolesOrAccessOnly` | Application roles/access only | 5 |
| `clientOrSensitiveDataAccess` | Client or sensitive data access | 10 |

### Q8 — Data (`Custom.DoraQ8DataImpact` → `Custom.DoraQ8Score`)

| Value | Label | Score |
|---|---|---:|
| `none` | No | 0 |
| `queryingOrPresentingData` | Querying or presenting data | 5 |
| `updatingNonClientNonSensitiveData` | Updating non-client/non-sensitive data | 10 |
| `updatingClientOrSensitiveData` | Updating client or sensitive data | 20 |

### Thresholds

| Score range | `Custom.DoraFinalRiskClass` | `Custom.DoraSuggestedTestProfile` |
|---|---|---|
| 10 – 40 | `Low` | `Low` |
| 41 – 70 | `Medium` | `Medium` |
| 71 – 104 | `High` | `High` |

> Note the implemented bounds are **10–104**, not the policy document's 0–110. Because Q1 has no zero-score answer, the minimum reachable explicit score is 10. (The arithmetic maximum over the answer set is in fact 101 — Q1 20 + Q2 20 + Q3 15 + Q5 8 + Q6 8 + Q7 10 + Q8 20, with Q4 scoring 0 because a `yes` there suppresses Q5's 8 — so the band's upper bound of 104 is never reached.) Thresholds are labelled *indicative* in the policy.

### Calculation

```
score = Q1 + Q2 + Q3 + Q4 + (Q5 if Q4 == "no" else 0) + Q6 + Q7 + Q8

if   score <= 40: class = "Low"
elif score <= 70: class = "Medium"
else:             class = "High"
```

### Incomplete state

If any applicable question is unanswered, the extension writes:

```
Custom.DoraClosureAllowed       = false
Custom.DoraFinalRiskClass       = ""
Custom.DoraFinalRiskScore       = 0
Custom.DoraSuggestedTestProfile = ""
```

and blocks the move to **Done** with: *"Complete the explicit DORA questionnaire before moving this PBI to Done."*

A skill must **never** fill an unknown answer with the lowest-scoring option to escape this state.

---

## 6. Test catalogue and the final test set

Twelve test items are defined. Each has a `minimumProfile`; a test is **suggested** when the PBI's suggested profile is at or above it (`Low < Medium < High`). `Optional` items are never auto-suggested.

| Key | Label | Min. profile | Performed by | Evidence hint |
|---|---|---|---|---|
| `unitTests` | Unit Tests | Low | Team (automated) | Link to automated test results |
| `automatedE2E` | Automated E2E | Low | Team (automated) | Link to automated test results |
| `smokeTesting` | Smoke Testing | Low | PO, delegate, or automated | Positive-test confirmation in the PBI, or linked automated tests |
| `automatedSecurityTesting` | Automated Security Testing | Low | Security teams (automated, e.g. ORCA) | Link to test results |
| `functionalAcceptanceTesting` | Functional / Acceptance Testing | Medium | PO or delegate | Link to child test tasks or a UAT report |
| `integrationTesting` | Integration Testing | Medium | Team, PO, delegate, or automated | Link to test results |
| `regressionTesting` | Regression Testing | Medium | Team, PO, delegate, or automated | Link to test results |
| `endUserTesting` | End User Testing | High | End user | Link to child test tasks or a UAT report |
| `performanceTesting` | Performance Testing | High | Team | Link to test results |
| `penetrationTesting` | Security Testing (Penetration Testing) | High | Security Red Team | Link to results, or report attached to the PBI |
| `redTeamConsultation` | Security Testing (Red Team consultation) | **Optional** | Team + Security Red Team | Summary of the outcome |
| `rollbackPlan` | Rollback Plan | **Optional** | Team or PO | Plan available before starting the PBI, plus evidence of execution |

> The implemented profile mapping differs from the policy prose in two places: **End User Testing is `High`** here (the policy narrates end-user testing under Medium), and **Red Team consultation / Rollback Plan are `Optional`** rather than Medium-mandatory. Skills follow the **implementation**, and should flag the divergence rather than silently reconciling it.

### Status values and effective status

Every test has three fields: `…Status`, `…Evidence`, `…Motivation`. Status is one of `NotRequired | Required | OptedIn | OptedOut`.

The effective status is derived, not free-form:

```
suggested = profileRequires(suggestedProfile, item.minimumProfile)

if suggested and status == "OptedOut":  effective = "OptedOut"
elif suggested:                          effective = "Required"
elif status == "OptedIn":                effective = "OptedIn"
else:                                    effective = "NotRequired"

inFinalSet         = effective in ("Required", "OptedIn")   # → evidence required
requiresMotivation = effective in ("OptedOut", "OptedIn")   # → motivation required
```

So: **opt-out** removes a suggested test but demands a motivation; **opt-in** adds an unsuggested test and also demands a motivation. Both motivations stay visible in the PBI.

### Evidence completeness and the Done gate

```
Custom.DoraEvidenceComplete =
      every test with inFinalSet has non-blank Evidence
  AND every test with requiresMotivation has non-blank Motivation
```

When `System.State` becomes `Done` and this is false, the extension blocks with: *"Provide evidence for every required DORA test, and a motivation for every opted-in/opted-out test, before moving this PBI to Done."*

---

## 7. Field reference (complete)

All fields are on the `Product Backlog Item` work item type. `Picklist` values are **not** enforced by the ADO field definition (they are free-form strings validated only by the form) — so a skill writing via REST **must** write exact values itself.

### Core

| Field | Type | Values |
|---|---|---|
| `Custom.DoraInScope` | Boolean | derived from the `Change` tag; hidden in the form |
| `Custom.DoraFlowType` | Picklist | `Implicit` \| `Explicit` |
| `Custom.DoraFinalRiskScore` | Integer | computed |
| `Custom.DoraFinalRiskClass` | Picklist | `Low` \| `Medium` \| `High` |
| `Custom.DoraSuggestedTestProfile` | Picklist | `Low` \| `Medium` \| `High` |
| `Custom.DoraClosureAllowed` | Boolean | computed; gates Done |
| `Custom.DoraEvidenceComplete` | Boolean | computed; gates Done |

> **Both computed flags are written by a work-item form contribution, which never executes on a REST write.** A stored value can therefore be arbitrarily stale — and a stale `true` is a false compliance assurance, worse than no check at all. Skills must **recompute** both from the twelve status/evidence/motivation fields (§6) and refuse to close on a mismatch, never trusting the stored value.

### Questions and scores

`Custom.DoraQ1SlaRating` … `Custom.DoraQ8DataImpact` (strings, values per §5) and `Custom.DoraQ1Score` … `Custom.DoraQ8Score` (integers, computed).

### Test evidence — 12 × 3 fields

For each key in the catalogue: `Custom.DoraTest<K>Status`, `Custom.DoraTest<K>Evidence`, `Custom.DoraTest<K>Motivation`, where `<K>` is one of:

`UnitTests`, `AutomatedE2E`, `SmokeTesting`, `AutomatedSecurityTesting`, `FunctionalAcceptanceTesting`, `IntegrationTesting`, `RegressionTesting`, `EndUserTesting`, `PerformanceTesting`, `PenetrationTesting`, `RedTeamConsultation`, `RollbackPlan`.

### Legacy fields — do not use

The org also carries older fields from a previous cycle: `Custom.DORA`, `Custom.DORArisk`, `Custom.DORAmeasures`, `Custom.DORA_4_eyes`, `Custom.DORA_all_measures_taken`, `Custom.DORA_automated_test`, `Custom.DORA_functional_test`, `Custom.DORA_no_risk`, `Custom.DORA_pentest`. These belong to the **application/team-level** DevOps Risk Assessment, not to this per-change process. Skills must never read or write them.

---

## 8. Where this lands in the dobby lifecycle

```
dobby-create-pbi ──→ scope touchpoint: apply the `Change` tag when the PBI is
                   │  a significant IT change (no scoring, no field writes)
                   ↓
dobby-update-pbi ──→ refinement: scope decision + risk assessment  (§9)
                                ↓ writes Q1–Q8, flow, class, profile
                                ↓ writes Status for every one of the 12 tests
                                ↓
dobby-close-pbi ────→ closure: register evidence + motivations       (§10)
                                ↓ writes Evidence/Motivation where they apply
                                ↓ recomputes the gates, requires human attestation
                                ↓ only then sets State = Done
```

> **`dobby-implement-pbi` is deliberately not part of this flow.** In the `combined` scenario it `reuse`s the **github** source, so there is no legal place to put ADO-specific DORA prose without either editing an off-limits file or forking the skill. Every artefact it might pre-stage (build runs, PR links, test results) is re-derivable at closure, so `dobby-close-pbi` harvests it there instead.
>
> `dobby-propose-from-pbi` is likewise untouched: it generates an OpenSpec change and writes no DORA fields.

---

## 9. Refinement: the risk-assessment step

**Owner skills:** `skills/ado/dobby-update-pbi` (refinement mode), `skills/ado/dobby-create-pbi`, and `combined` where it reuses the ADO flow.
**Trigger:** refinement of a PBI, or an explicit "do the DORA assessment for #N".
**Placement:** a new phase after the existing refinement synthesis (R5) and before applying changes (R7) — the assessment needs the refined description to reason over.

### Steps

1. **Read state.** Fetch the work item including `System.Tags`, `System.State`, `System.Rev`, and all `Custom.Dora*` fields. Record `System.Rev` — it stamps the assessment so staleness is detectable.
2. **Scope decision.** Determine whether the PBI is a significant IT change (§2). Quote the supporting text. If out of scope, report why, stop, and do not touch DORA fields.
3. **Ensure the `Change` tag.** In scope but untagged → propose adding `Change` (this is what makes the DORA panel appear). Never remove the tag.
4. **Implicit criteria.** Test both knockouts against evidence in the PBI. If one holds, propose `FlowType = Implicit` with the criterion named and quoted.
5. **Explicit questionnaire.** If neither holds, walk Q1–Q8. For each question present: the proposed answer value, its label, its score, and the PBI text (or user answer) that justifies it. Respect the Q4 → Q5 skip rule.
6. **Missing information.** Any question that cannot be justified from the PBI is `Unknown`. Ask the user, or record it as a visibly marked `assumption` for review. **Never** default an unknown to the lowest-scoring option, and never treat a missing SLA field as Bronze.
7. **Compute.** Show the arithmetic, the total, the threshold band, and the resulting class and suggested profile.
8. **Derive the final test set.** From the suggested profile, list suggested tests. Opt-ins may be proposed (they only add coverage); **opt-outs must never be proposed by the skill** — record one only when the user states it explicitly, with a motivation. Recompute the effective status per §6.
9. **Present the draft** using the report format in §11 and get explicit confirmation.
10. **Write fields** (see §12). Write the flow, the answers, the scores, the class, the profile, and a `Status` for **every** one of the 12 tests — including `NotRequired` for those outside the set.
11. **Add a discussion comment** carrying the full assessment table plus the AI-draft banner (§13). Post the reasoning **before** the field writes so review happens against a durable record. For an implicit-Low PBI this comment is **mandatory**: there is no field for the criterion that applied (`DORA_IMPLICIT_CRITERIA` is UI copy with no `fieldRef`), so the comment is the primary audit artefact and must name the criterion and quote the substantiating PBI text. Should the extension owners later ship a `Custom.DoraImplicitCriterion` field, `azdo-dora.py` can write it via `--implicit-criterion-field` without further rework.

Leave `Custom.DoraClosureAllowed` and `Custom.DoraEvidenceComplete` to the closure flow, which recomputes them from the twelve test rows (§6). Refinement writes neither.

---

## 10. Closure: registering test results

**Owner skills:** `skills/ado/dobby-close-pbi`, `skills/combined/dobby-close-pbi`, and the closure phase of `dobby-implement-pbi`.
**Placement:** a new phase between *Gather Implementation Evidence* (step 4) and *Close the PBI* (step 8). It must run **before** the state transition, because the extension gates Done.

### Steps

1. **Read the assessment.** Fetch all `Custom.Dora*` fields.
   - `DoraInScope = false` → no DORA work; close normally and say so.
   - In scope but `DoraFlowType` empty, or `FinalRiskClass` empty → **the assessment was never completed**. Stop and route the user back to refinement (§9). Do not close.
2. **Rebuild the final test set** from `DoraSuggestedTestProfile` and the twelve `…Status` fields using the §6 rules. Never re-derive it from the score alone.
3. **Harvest candidate evidence** from what the close flow already gathers: build/release runs, test-results tabs, PR links, commits, child test tasks, ORCA scan links in the PR, and screenshots. Map each candidate to a test key.
4. **Fill the gaps by asking.** For each `inFinalSet` test lacking evidence, ask specifically — the evidence hint in §6 is the prompt. For each `OptedIn`/`OptedOut` test lacking a motivation, ask for the motivation.
5. **Assess evidence quality, separately from classification.** Produce the table in §11. A link is **not** proof that a test passed; only claim *Sufficient* when the referenced content actually says so, or the user confirms it.
6. **Write evidence and motivation fields.**
7. **Verify the gates by recomputation.** Re-read the work item and recompute `DoraEvidenceComplete` and `DoraClosureAllowed` from the twelve test rows — never trust the stored values, including a stored `true`. Report exactly which test keys are missing evidence or motivation and **do not** attempt the transition while any remain. Missing evidence is a gap; it is never resolved by opting the test out.
8. **Obtain explicit human attestation** that the evidence is accurate and complete, and record who attested and when. Only then write the two gate flags.
9. **Post the closing comment** with the DORA evidence section appended to dobby's existing closing summary, carrying the AI-draft banner, the source `System.Rev`, and the attestation.
10. **Close** — re-read and verify the flags, then set `System.State = Done`. Never write `ClosureAllowed = true` and transition in a single action.

### Evidence formats accepted

Pipeline/test-run link · child test-task link · UAT report · ORCA result link · penetration-test report · positive manual confirmation · Red Team consultation summary · attached report · documented opt-in/opt-out motivation.

### Organizational evidence guidance (not policy rules — label as such)

- If a link fails, request a screenshot or a working alternative link.
- If data anonymization applies, explain its setup; if it does not apply, state that.
- Screenshots should be full-screen captures with a visible timestamp.

### ORCA (automated security testing)

ORCA is the current automated-security-testing mechanism; the extension is installed centrally and a project needs an ORCA service connection (the central cloud platform team can create one). Scan types: `iac`, `image`, `sast`, `sca`, `secrets`.

The skill may ask which scan types apply, whether the pipeline result is linked, whether the scan completed, and whether findings were resolved, accepted, or suppressed with justification. It must **not** prescribe a scan type from the DORA classification alone — applicability depends on the artefacts.

---

## 11. Report format

Skills emit this Markdown, both to the user and (condensed) into the PBI discussion comment.

```markdown
# DORA for DevOps Assessment

> AI-generated draft. Human review is required.
> This is not an approval or compliance decision.
> Source PBI revision: <System.Rev> · generated <date>

## PBI
- ID / Title / Revision / Change tag
- Significant IT change: Yes | No | Unknown

## Scope decision
**Decision:** · **Evidence:** · **Missing information:**

## Implicit assessment
| Criterion | Result | Evidence |
|---|---|---|
| Bronze SLA or no Silver/Gold dependency | Yes/No/Unknown | |
| Immediate safe rollback / roll-forward | Yes/No/Unknown | |

**Implicit classification:** · **Explicit assessment required:**

## Explicit assessment
| Question | Answer (value) | Score | Evidence |
|---|---|---:|---|
| Q1 SLA | | | |
| ... | | | |

**Total:** · **Class:** · **Suggested test profile:**

## Test plan
| Test | Suggested | Effective status | Performed by | Evidence required | Status |
|---|---|---|---|---|---|

## Deviations
| Test | Direction (opt-in/opt-out) | Motivation | Reviewer |
|---|---|---|---|

## Evidence assessment
| Test | Evidence | Result | Gap |
|---|---|---|---|

## Open questions

## Human decision
- Reviewed by / Role / Date / Decision
```

---

## 12. Implementation notes for the skills

### Writing the fields

`Custom.Dora*` are plain (non-multiline) fields, so they can be PATCHed directly. **Implemented as `skills/_lib/azdo-dora.py`**, a dedicated helper with `catalog` / `score` / `read` / `check` / `write-assessment` / `write-evidence` / `finalize` subcommands.

`azdo-update-fields.py` was deliberately **not** extended: its `--field <ref>=<FILE>` signature takes a *file path* and forces `multilineFieldsFormat: Markdown`, which is incompatible with the ~40 scalar picklist / integer / boolean fields this process writes.

The scoring, the Q4→Q5 skip, the effective-status derivation, the applicability matrix, and the completeness rules are real logic that must not live in prose. The script follows the existing `_lib` conventions — Python 3 stdlib only, the `AZURE_DEVOPS_EXT_PAT` → `ADO_TOKEN` → `az account get-access-token` auth chain, and retry-with-backoff on 429/502/503/504. It is bundled under `dobby-update-pbi` and referenced by `dobby-close-pbi` (both `ado` and `combined`).

Guardrails are enforced in code, not only in prose: the writable-field whitelist excludes the legacy `Custom.DORA*` fields; blank and `unknown` answers are rejected rather than defaulted; `Q4 = yes` writes `Q5 = no` explicitly; Evidence is accepted only for `Required`/`OptedIn` rows and Motivation only for `OptedIn`/`OptedOut`; an `OptedOut` status requires an explicit user-requested flag plus a motivation; and `finalize` refuses to write the gate flags without an attestor or with any gap outstanding.

`scripts/dora-selfcheck.py` exercises the scoring boundaries, the derivation table, and every guardrail offline.

### Reading the fields

`az boards work-item show --id <id> --organization <org> --output json` returns all `Custom.Dora*` fields, and `azdo-dora.py read` returns the same state already derived. Per the existing skill rules, run either standalone and reason over the full JSON — no piping.

### Scenario coverage

- **`ado`** — full support: the `Change`-tag scope touchpoint in `dobby-create-pbi`, the assessment phase in `dobby-update-pbi`, the evidence phase in `dobby-close-pbi`.
- **`combined`** — the work item lives in ADO, so `create` / `update` / `propose` already reuse `ado` and inherit the assessment unchanged. `combined/dobby-close-pbi` carries the same evidence phase on its ADO side, harvesting GitHub PR, commit, and pipeline links as evidence values.
- **`github`** — **out of scope.** DORA-for-DevOps is defined against ADO PBI fields; there is no GitHub Issue equivalent. Do not add DORA prose to the github-scenario sources.
- **`dobby-implement-pbi`** — untouched in every scenario (see §8).

After editing sources, regenerate and verify:

```bash
python scripts/build-skills.py dev
python scripts/check-skill-sync.py
```

Eval cases live under the touched skills' `evals/evals.json` (`skills/ado/dobby-update-pbi/` and `skills/ado/dobby-close-pbi/`) and cover: an out-of-scope PBI, an implicit-Low PBI, an answer that must be marked as an `assumption`, an unknown answer that must not become the lowest score, an opt-out without motivation, a recomputed `DoraEvidenceComplete = false`, a **stale stored `true` that must not be trusted**, a **closure attempt without attestation that must not write**, and a **missing-evidence case where opting out is the tempting shortcut and must not be taken**. `run-skill-evals.py` emits manual run sheets rather than executing anything — a green validation count is not proof of behaviour.

---

## 13. Guardrails (non-negotiable for the skills)

The skill **must**:

- quote or point to the PBI information supporting each answer;
- use `Unknown` when information is absent, and ask;
- never convert `Unknown` to the lowest score;
- never assume Bronze from the absence of an SLA field;
- never assume rollback is safe merely because a deployment can technically be repeated — distinguish *rollback capability* from *rollback without permanent damage*;
- never infer that a test passed from the presence of a link or an unchecked checkbox;
- never fabricate evidence — write nothing where no artefact was located, and report the test as an open gap;
- never propose or write an `OptedOut` status to resolve missing evidence; an opt-out is valid only when the user stated it explicitly, with a motivation;
- never trust a stored `DoraEvidenceComplete` / `DoraClosureAllowed` value — always recompute from the twelve test rows;
- never read an unrecognized `SuggestedTestProfile` (empty, mis-cased, localized) as "no tests required" — it is a hard blocker that forces a re-assessment, because a silent default there turns an unevidenced High change green;
- clear evidence and motivation from rows that a re-assessment or an opt-out made inapplicable, and reset `DoraEvidenceComplete` when re-assessing — evidence gathered under a previous test set does not carry over;
- never use the out-of-scope write as an escape hatch: it is refused while the `Change` tag is present, and refused on an already-assessed PBI unless the user explicitly discards the earlier assessment;
- require explicit human attestation before writing the gate flags, and record who attested and when;
- never treat `System.State = Done` as proof the assessment happened (form validation is bypassable via bulk edit, REST, imports, and automations — a known governance gap); inspect the DORA fields instead;
- show the arithmetic and the threshold band;
- flag policy wording marked *indicative* or *unresolved*;
- retain every opt-in / opt-out motivation;
- separate policy requirements from recommendations;
- require human review before writing or approving the assessment.

Every generated assessment carries:

```
> AI-generated DORA assessment draft.
> Human review is required.
> This output is not an approval or compliance decision.
```

plus the source `System.Rev` and generation date, so stale drafts are detectable.

### Do not confuse with the application/team risk cycle

| PBI-level DORA for DevOps | Application/team DevOps Risk Assessment |
|---|---|
| Per significant change | Periodic, per application/team |
| Classifies the change Low/Medium/High | Assesses broader operational risks and controls |
| Selects tests for the change | Assesses mitigating measures |
| Evidence stored on the PBI | Evidence via templates and risk folders |
| Uses `Custom.Dora*` fields | Uses the legacy `Custom.DORA*` fields (§7) |

If a request mentions CIAA, the annual assessment cycle, sample selection, or Bwise, ask which process is meant.

---

## 14. Open questions — represent as unresolved, do not harden into rules

- Whether the 2-hour mitigation boundary is final (marked *indicative*).
- Whether the scores and thresholds are final (marked *illustrative/indicative*); the implemented range is 10–104 vs. the documented 0–110.
- How unit testing applies to **data changes** — explicitly unresolved. Recommended skill handling: *"Applicability unresolved by policy for this change type; document the closest appropriate automated validation, or motivate the opt-out. Human decision required."*
- Whether automated E2E should depend on product type.
- Whether integration testing stays a separate test (it overlaps automated and acceptance testing).
- Whether risks should be named explicitly as Confidentiality / Integrity / Availability.
- How the Automated Security Testing (ORCA) process operates in practice — pilot feedback says it is unclear.
- Whether the duplicated DORA performance and end-to-end statements are removed from the shared Definition of Done (an open Way-of-Working task proposes removal; still *To Do*). Safe wording: the minimum DoD **still contains** them while removal is proposed.
- Enforcement across bulk edits, APIs, imports, and automations — the proposed remediation is inherited process rules on the Done transition plus automation.
- How existing PBIs are backfilled or validated.
- **The final mandatory rollout date.** The documents are titled *valid from 1 September 2026*; teams could practise from 1 July; a proposal moved implementation to 1 October (the pilot overlapped the holiday season), and another proposed making it dependent on the extension's availability. **No confirmed final decision was found.** A skill must not claim 1 October is final — report the ambiguity and point to the current announcement or the policy owner.

Two further divergences found while verifying the extension, worth raising with the policy owners:

- **End User Testing** is `High` in the implementation but narrated under Medium in the policy.
- **Red Team consultation** and **Rollback Plan** are `Optional` (opt-in only) in the implementation, but described as Medium-level tests in the policy.

---

## 15. Compact knowledge block

```yaml
name: DORA for DevOps
organization: internal
assessment_unit: Product Backlog Item
scope_signal: System.Tags contains "Change"   # -> Custom.DoraInScope

implicit_low_any_of:
  - bronze SLA, or no Silver/Gold application dependency
  - immediate rollback/roll-forward without permanent damage
implicit_written_state: {flow: Implicit, score: 10, class: Low, profile: Low, closureAllowed: true}
out_of_scope_state:    {inScope: false, score: 0, class: Low, profile: Low, closureAllowed: true}

explicit_scoring:
  Q1_sla:         {silver: 10, gold: 20}
  Q2_mitigation:  {withinTwoHoursNoDataCorruptionRisk: 0, notWithinTwoHoursOrDataCorruptionRisk: 20}
  Q3_impact:      {contentOnly: 0, bugfixOrSmallBusinessLogicChange: 5, mediumBusinessLogicChange: 10, largeBusinessLogicOrArchitectureChange: 15}
  Q4_new_func:    {no: 0, yes: 3}   # yes => skip Q5, force Q5=no
  Q5_incidents:   {no: 0, some: 3, many: 8}
  Q6_familiarity: {dailyOperationOrFamiliarCode: 0, unfamiliarProductModuleOrCode: 3, outsideControlThirdPartyOrOtherTeams: 8}
  Q7_auth:        {none: 0, applicationRolesOrAccessOnly: 5, clientOrSensitiveDataAccess: 10}
  Q8_data:        {none: 0, queryingOrPresentingData: 5, updatingNonClientNonSensitiveData: 10, updatingClientOrSensitiveData: 20}
thresholds: {Low: 10-40, Medium: 41-70, High: 71-104}

test_profiles:
  Low:      [unitTests, automatedE2E, smokeTesting, automatedSecurityTesting]
  Medium:   [+ functionalAcceptanceTesting, integrationTesting, regressionTesting]
  High:     [+ endUserTesting, performanceTesting, penetrationTesting]
  Optional: [redTeamConsultation, rollbackPlan]   # opt-in only

test_status: [NotRequired, Required, OptedIn, OptedOut]
evidence_required_when: status in (Required, OptedIn)
motivation_required_when: status in (OptedIn, OptedOut)
done_gates: [Custom.DoraClosureAllowed, Custom.DoraEvidenceComplete]

evidence_rule: never infer successful execution from the presence of a link alone
approval: {ai_output: draft_only, human_review: mandatory}
```
