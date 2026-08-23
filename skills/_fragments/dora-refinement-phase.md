Azure DevOps carries a per-change **DORA for DevOps** risk assessment on the PBI (work-item form group "DORA"). This phase produces a complete, prefilled, evidence-backed draft; a human reviews and confirms it before anything is written.

`azdo-dora.py` owns the questionnaire values, the scores, the thresholds, the test catalogue, the effective-status derivation, and the completeness rules. **Never re-derive any of them in your own reasoning** — call the script and read its output.

**D1. Read the current state**

```bash
python skills/_lib/azdo-dora.py read --work-item-id <id> --org "<org-url>" --project "<project-name>"
```

Record `rev` — it stamps the assessment so staleness is detectable later. If `doraFieldsPresent` is `false`, the organization has not installed the DORA extension: say so, skip this phase entirely, and continue the refinement.

**D2. Scope decision — is this PBI a significant IT change?**

Scope is driven **purely by the `Change` tag** (`System.Tags` contains `Change` → `Custom.DoraInScope`). Decide from the refined description, not the title:

| Situation | Action |
|---|---|
| Not a significant IT change (investigation/spike, documentation, onboarding, manual data entry, data updates with **unchanged** reusable scripts) | Report why, quote the supporting text, and stop. Do not add the tag. |
| Significant IT change (code, changed scripts, technical/configuration changes) | Propose adding the `Change` tag if absent; never remove it. Continue. || Cannot tell from the available text | Say exactly what is missing (does code, script, configuration, authentication, data processing, or runtime behaviour change?) and ask. |

With the user's agreement, add the tag before writing any assessment (the helper refuses an in-scope write while the tag is absent):

```bash
az boards work-item update --id <id> --fields "System.Tags=Change; <every-existing-tag>" --organization "<org-url>" --output json
```

`System.Tags` is **replaced**, not appended — repeat every tag already on the PBI (from step D1's read) in the same value, or they are lost.
Never read `FinalRiskClass = Low` as an assessment result without first checking `DoraInScope` — the out-of-scope state writes exactly that. A `bypass` tag may be present; **read** it, report it, and never set it.

For an out-of-scope PBI you may record the neutral state explicitly:

```bash
python skills/_lib/azdo-dora.py write-assessment --work-item-id <id> --org "<org-url>" \
    --project "<project-name>" --plan <path-to-plan.json>
```

with `{"scope": "out", "outOfScopeReason": "<why>"}`. Then stop this phase. The helper refuses this write when the `Change` tag is present (resolve the contradiction with the user first) and when a completed assessment already exists — pass `--discard-existing-assessment` only when the user explicitly decided the earlier assessment was wrong.

**D3. Implicit knockout criteria**

An in-scope PBI takes the **implicit** path when **at least one** knockout criterion holds:

1. **Bronze SLA** — the change concerns a business application with a Bronze SLA, or a component not used by any Silver- or Gold-rated business application.
2. **Immediate mitigation** — rollback, roll-forward, or disabling can immediately revert the change without permanent damage, including no already-corrupted database records.

Test both against evidence in the PBI. "Low by default" is not "low without reasoning": the plan must name the criterion and quote the substantiating PBI text, and the script rejects an implicit plan that lacks either. `FinalRiskScore = 10` is a **sentinel**, not a computed sum.

There is no field for the criterion that applied, so **the assessment comment (D7) is the primary audit artefact for an implicit-Low PBI and is mandatory.**

**D4. Explicit questionnaire — prefill Q1–Q8**

If neither criterion holds, prefill all eight answers as completely as possible. Ground each answer in PBI text, acceptance criteria, or code you actually inspected, and cite that basis.

- An answer you could **not** ground goes into `assumptions` with a short note, so it is visibly marked as an `assumption` in the report rather than blended in with cited answers.
- **Never** default an unknown to the lowest-scoring option, and never assume Bronze from a missing SLA field — the script rejects blank and `unknown` answers outright rather than letting one through.
- Q6 (familiarity) was flagged as unclear in the pilot: explain it, do not just present it.
- `Q4 = yes` skips Q5; the script writes `Q5 = no` explicitly, because a blank Q5 keeps the item incomplete.

**D5. Test set, opt-ins and opt-outs**

The suggested profile follows from the class. Opt-ins **add** coverage and you may propose them; **never propose or write an opt-out.** Opting out clears `requiresEvidence`, which makes it the cheapest possible route to a green gate — an `OptedOut` status is valid only when the user stated it explicitly. Every opt-in and opt-out needs a motivation (the script refuses without one).

Two implementation-vs-policy divergences are real and must be surfaced, not reconciled: **End User Testing is `High`**, and **Red Team consultation / Rollback Plan are `Optional`** (opt-in only).

**D6. Resolve and present the draft**

Write the plan to a JSON file:

```json
{
  "scope": "in",
  "flow": "Explicit",
  "sourceRev": 12,
  "answers": {"q1": "silver", "q2": "withinTwoHoursNoDataCorruptionRisk", "q3": "bugfixOrSmallBusinessLogicChange",
              "q4": "no", "q5": "no", "q6": "dailyOperationOrFamiliarCode", "q7": "none", "q8": "queryingOrPresentingData"},
  "assumptions": [{"question": "q6", "note": "No familiarity signal in the PBI or comments."}],
  "optIns": ["rollbackPlan"],
  "optOuts": [],
  "motivations": {"rollbackPlan": "Schema migration; the user asked for a documented rollback."}
}
```

An implicit plan instead carries `"flow": "Implicit"`, `"implicitCriterion"` (`bronzeSla` or `immediateMitigation`), and `"implicitEvidence"` (the quoted PBI text).

Render the report — this is the §11 format, with the AI-draft banner, the arithmetic, the threshold band, the test plan, the deviations, and the divergences:

```bash
python skills/_lib/azdo-dora.py score --plan <path-to-plan.json> --report
```

Show it to the user in full and ask for confirmation. **Post the same reasoning to the PBI discussion before any field write** so the review happens against a durable record:

```bash
python skills/_lib/azdo-add-comment.py --work-item-id <id> --org "<org-url>" \
    --project "<project-name>" --file <path-to-assessment.md>
```

**D7. Write the fields**

Only after explicit confirmation:

```bash
python skills/_lib/azdo-dora.py write-assessment --work-item-id <id> --org "<org-url>" \
    --project "<project-name>" --plan <path-to-plan.json>
```

This writes the flow, the answers, the scores, the class, the profile, and a `Status` for **all twelve** tests (including `NotRequired`), plus the opt-in/opt-out motivations — with the exact picklist strings, which the ADO field definitions do not enforce. Add `--dry-run` first if you want to inspect the patch operations.

It also clears any motivation and evidence that no longer applies to a row, and resets `Custom.DoraEvidenceComplete` to `false` — a re-assessment invalidates evidence gathered under the previous test set, and a leftover `true` would be a stale green gate. `Custom.DoraClosureAllowed` is set to `true` because the questionnaire is now complete; the closure flow recomputes both. Evidence is **not** written here: it belongs to closure, where artefacts actually exist.

**Never** read or write the legacy `Custom.DORA*` fields (`Custom.DORArisk`, `Custom.DORA_4_eyes`, …) — they belong to the periodic application/team risk cycle, not to this per-change process. The script's field whitelist enforces this. If a request mentions CIAA, the annual cycle, sample selection, or Bwise, ask which process is meant.

**D8. Open questions to report as unresolved (never harden into rules)**

The 2-hour mitigation boundary, the scores and thresholds (all marked *indicative*), unit testing for data changes, ORCA's practical operation, and the final mandatory rollout date are open. Report them as open; do not present them as settled.
