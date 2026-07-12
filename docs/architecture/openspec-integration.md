# OpenSpec integration — current state and the OPSX transition

Status: decided 2026-07-11 (issue #11). Revisit when OpenSpec removes the classic
skill names or changes the artifact CLI surface.

## How dobby drives OpenSpec

Dobby's propose/implement/close skills integrate with OpenSpec at **two layers**:

1. **CLI layer** (propose skills, close's archive step): dobby calls the
   `openspec` CLI directly — `openspec new change`, `openspec instructions
   <artifact-id> --change`, `openspec status --change --json`, `openspec
   archive`. This *is* the artifact-guided workflow that OPSX wraps; it is not
   the legacy all-at-once flow. No change needed here for the OPSX transition.
2. **Skill layer** (implement's Phase 5, propose's closing hint): dobby refers
   to the OpenSpec-installed apply skill. OpenSpec is renaming its skills —
   classic `openspec-apply-change` → OPSX `opsx:apply` — and a project may have
   either, depending on when `openspec init`/`openspec update` last ran.

## Decision

- **Skill-name references are version-tolerant**: dobby prose names both forms
  ("`opsx:apply` (current OPSX workflow) or `openspec-apply-change` (older
  installs); use whichever is present") instead of pinning one. Dobby does not
  bundle openspec skills, so it cannot know which set a project has.
- **The CLI layer stays as-is** — it already targets the artifact flow.
- **Traceability invariants are dobby's, not OpenSpec's, and are preserved in
  either flow**: change names `pbi-<id>-<slug>` / `issue-<id>-<slug>`, and the
  `> Source: … [#<id>](<url>) — "<title>"` line in `proposal.md`.

## Classic ↔ OPSX mapping (for reference)

| Classic skill | OPSX skill | Used by dobby |
|---|---|---|
| `openspec-propose` | `opsx:propose` | No — `dobby-propose-from-pbi` replaces it (adds tracker fetch, refinement, traceability) |
| `openspec-apply-change` | `opsx:apply` | Yes — implement Phase 5 (version-tolerant reference) |
| `openspec-archive-change` | `opsx:archive` | Indirectly — close flows call `openspec archive` (CLI) |
| `openspec-explore` | `opsx:explore` | No |

## OpenSpec Stores (beta) — evaluated, skipped for now

Stores would allow cross-repo shared specs. Considered for the `combined`
scenario (ADO work items + GitHub repo): **not adopted**, because in combined
mode there is still exactly one code repository — the OpenSpec change lives in
that repo's `openspec/` directory, and the ADO side holds only work-item state,
not specs. There is no cross-repo spec to share.

**Revisit trigger**: a scenario where specs must span multiple repositories
(e.g. one work item implemented across several services), or Stores leaving
beta with a compelling single-repo benefit.
