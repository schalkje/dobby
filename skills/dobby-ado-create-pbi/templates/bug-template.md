# Bug Template

> This template maps to three Azure DevOps work item fields for **Bug** type.
> All fields are stored as **Markdown** (not HTML).
> When creating or refining a Bug, each section below populates its corresponding field.

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     AZURE DEVOPS FIELD: Repro Steps  (Microsoft.VSTS.TCM.ReproSteps — markdown format)
     This is the PRIMARY content field for Bugs (equivalent to Description for PBIs).
     ═══════════════════════════════════════════════════════════════════════════ -->

## 🐞 Summary

> *One or two sentences describing the defect. Reference the relevant FR if applicable.*

## ⚠️ Current Behavior

> *What actually happens. Include screenshots (as `![alt](attachment-url)`) if available.*

## ✅ Expected Behavior

> *What should happen instead, per design docs or acceptance criteria.*

## 🔁 Steps to Reproduce

1. Step one
2. Step two
3. Step three

## 📐 Design Reference

| Type | Reference |
| --- | --- |
| Requirement | FR-XXX-NNN |
| Design doc | `docs/design/...` |
| Component | `src/renderer/...` |

## 🧩 Root Cause (if known)

> *Brief analysis of what's causing the bug. Reference specific code if applicable.*

## 🛠️ Fix Direction (if known)

> *Suggested approach to fix the issue.*

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     AZURE DEVOPS FIELD: Description  (System.Description — markdown format)
     For Bugs, this is a SECONDARY field. Keep it brief — most detail goes
     in Repro Steps above.
     ═══════════════════════════════════════════════════════════════════════════ -->

> *Optional: brief context that doesn't fit in Repro Steps — e.g., environment info,
> related work items, or background on when the bug was introduced.*

### 👤 Stakeholder (optional)

| Role | Name / Group |
| --- | --- |
| Reporter | |
| Impacted stakeholder | |

### 🔗 Related Items

| Relation | Item |
| --- | --- |
| Parent | [#NNNN](https://dev.azure.com/<org>/<project>/_workitems/edit/NNNN) |
| Related | [#NNNN](https://dev.azure.com/<org>/<project>/_workitems/edit/NNNN) |

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     AZURE DEVOPS FIELD: Acceptance Criteria
     (Microsoft.VSTS.Common.AcceptanceCriteria — markdown format)
     When is the bug considered fixed? Each criterion must be independently verifiable.
     ═══════════════════════════════════════════════════════════════════════════ -->

- [ ] *Criterion describing the correct behavior after the fix*
- [ ] *Criterion for edge cases or related scenarios*
- [ ] *Criterion for regression prevention (e.g., "existing X still works")*

---

Template version 1.1 - Dobby Bug Framework
