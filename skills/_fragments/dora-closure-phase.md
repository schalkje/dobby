This phase runs **before** the Done transition, because Azure DevOps gates the transition on the DORA fields. `azdo-dora.py` owns the derivation and the completeness rules — call it; never re-derive them in prose or in your own reasoning.

**E1. Read the assessment and recompute the gates**

```bash
python skills/_lib/azdo-dora.py check --work-item-id <id> --org "<org-url>" \
    --project "<project-name>" --assessed-rev <rev-recorded-at-assessment> --report
```

`check` exits non-zero when closure is blocked. Handle each verdict:

| Verdict | What it means | Action |
|---|---|---|
| `doraFieldsPresent: false` | The organization has not installed the DORA extension | Skip this phase entirely; close normally and say so |
| Not in scope (no `Change` tag, and none recorded) | No DORA work | Close normally and say so |
| Assessed out of scope but the `Change` tag is now present | The earlier verdict is **void** | Stop. Require re-assessment via the refinement flow |
| In scope, `FlowType` or `FinalRiskClass` empty | The assessment was **never completed** | Stop. Route the user back to refinement. Do not close |
| In scope, `SuggestedTestProfile` not `Low`/`Medium`/`High` | The final test set **cannot be derived** — an unrecognized profile would make every test look `NotRequired` | Stop. Re-assess via the refinement flow. Never close on it |
| Revision drift since the recorded assessment | Tags or acceptance criteria may have changed | Compare Tags and Acceptance Criteria: re-assess if either changed; a revision bump caused only by dobby's own field writes is not a re-assessment trigger |

`System.State = Done` is **not** proof that an assessment happened — form validation is bypassable via bulk edit, REST, imports, and automations. Inspect the fields.

**Never trust the stored flags.** `Custom.DoraEvidenceComplete` and `Custom.DoraClosureAllowed` are computed by a work-item form contribution that never executes on a REST write, so a stored value can be stale — and a stale `true` is a false compliance assurance, worse than no check at all. `check` recomputes both from the twelve test rows and reports `evidenceCompleteMismatch`; on a mismatch, the recomputed value wins and closure is blocked.

**E2. Harvest evidence from real artefacts only**

The final test set comes from `check`'s `tests` array (the rows where `requiresEvidence` is true). Map the artefacts this close flow already gathers to those rows: pipeline/build and test-run links, PR and commit URLs, child test tasks, UAT reports, ORCA scan links, attached reports, and positive manual confirmations.

**Prefill evidence only from artefacts you actually located.** Evidence is a factual assertion that a test was performed; fabricating it manufactures an audit record that is indistinguishable downstream from a real one. Where no artefact exists, write **nothing** into the evidence field and report the test as an open gap.

`redTeamConsultation` and `rollbackPlan` are **always manual input** when opted in — never prefilled, never inferred.

Assess quality separately from classification: **a link is not proof that a test passed.** Only report a test as passed when the referenced content says so or the user confirms it. If a link fails, ask for a working alternative or a screenshot (full-screen, visible timestamp). These are organizational recommendations, not policy rules — label them as such.

For automated security testing, ORCA is the current mechanism (scan types `iac`, `image`, `sast`, `sca`, `secrets`). You may ask which scan types apply, whether the pipeline result is linked, whether the scan completed, and whether findings were resolved, accepted, or suppressed with justification. Do **not** prescribe a scan type from the DORA classification alone — applicability depends on the artefacts.

**E3. Write only the fields that apply**

| Effective status | Evidence | Motivation | What to write |
|---|---|---|---|
| `Required` | shown, required | hidden | Evidence only — from located artefacts, else leave blank as a gap |
| `OptedIn` | shown, required | shown, required | Both |
| `OptedOut` | hidden | shown, required | Motivation only |
| `NotRequired` | hidden | hidden | Nothing (Status was already written at refinement) |

Writing evidence to a `NotRequired` or `OptedOut` row pollutes the audit record and can make an un-run test look performed. The script rejects such a payload rather than writing it.

```json
{
  "unitTests": {"evidence": "https://dev.azure.com/org/proj/_build/results?buildId=4821 — 312 passed"},
  "rollbackPlan": {"evidence": "Rollback plan in the PBI description; executed in the staging run.",
                   "motivation": "Schema migration; the user asked for a documented rollback."}
}
```

```bash
python skills/_lib/azdo-dora.py write-evidence --work-item-id <id> --org "<org-url>" \
    --project "<project-name>" --evidence <path-to-evidence.json>
```

It exits non-zero and lists the remaining gaps by test key. Use `--dry-run` to inspect the patch operations first.

**E4. Gaps are gaps — opting out is not a remedy**

For every required test whose evidence you could not locate, name the test key and report it as an **open gap**. Ask the user for the evidence, using the row's `evidenceHint` as the prompt.

**Never propose or write an `OptedOut` status to resolve missing evidence.** Opting out clears `requiresEvidence`, so it is the cheapest possible route to a green gate — and taking it defeats the control with the very automation meant to enforce it. An `OptedOut` status is accepted only when the **user stated it explicitly**, and the script requires both `"userRequestedOptOut": true` and a motivation before it will write one. Applying an opt-out also **clears that row's evidence**, since an opted-out test was not performed. Opt-outs are re-confirmed with their motivations at the attestation gate.

Unit testing for **data changes** is explicitly unresolved by policy. Say so: *"Applicability unresolved by policy for this change type; document the closest appropriate automated validation, or motivate the opt-out. Human decision required."*

**E5. Human attestation, then the gate flags**

Present the report from `check --report`: the per-test evidence table, the quality assessment, the remaining gaps, and every opt-in/opt-out motivation. Ask the user explicitly to attest that the evidence is accurate and complete. Record **who attested and when**.

```bash
python skills/_lib/azdo-dora.py finalize --work-item-id <id> --org "<org-url>" \
    --project "<project-name>" --attested-by "<name>" --attested-at "<iso-8601>"
```

`finalize` recomputes completeness first and refuses to write anything when evidence is incomplete. It writes only `DoraEvidenceComplete` and `DoraClosureAllowed`.

**E6. Re-read, verify, and only then transition**

Never write `ClosureAllowed = true` and transition to Done in a single action. Re-read the work item and confirm both flags before the state change:

```bash
python skills/_lib/azdo-dora.py check --work-item-id <id> --org "<org-url>" --project "<project-name>"
```

If it still reports blockers, name the specific test keys and **do not** attempt the transition.

**E7. Append the DORA section to the closing comment**

Add to dobby's existing closing summary, carrying the AI-draft banner and the source `System.Rev`:

```markdown
### DORA for DevOps
- **Flow / Class / Suggested profile**: <flow> · <class> · <profile>
- **Final test set**: <N> tests, all with registered evidence
- **Deviations**: <test — direction — motivation, or "none">
- **Open questions**: <policy items reported as unresolved, or "none">
- **Attested by**: <name> on <date> — evidence reviewed and confirmed
```

Never read or write the legacy `Custom.DORA*` fields — they belong to the periodic application/team risk cycle, not to this per-change process.
