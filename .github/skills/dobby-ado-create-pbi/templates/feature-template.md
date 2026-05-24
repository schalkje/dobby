# Feature Template

> This template maps to two Azure DevOps work item fields for **Feature** type.
> Both fields are stored as **Markdown** (not HTML).
> When creating or refining a Feature, each section below populates its corresponding field.

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     AZURE DEVOPS FIELD: Description  (System.Description — markdown format)
     ═══════════════════════════════════════════════════════════════════════════ -->

## [Product] - [Feature Name]

> *One-sentence summary of the feature's business value and desired outcome.*

## 👥 Stakeholders

| Role | Name / Group |
| --- | --- |
| 👤 Business Stakeholder | |
| 🧠 Subject Matter Expert | |
| 🏗️ Technical Owner | |

---

## 🎯 Outcome

> *What business or product outcome this feature is expected to deliver.*

---

## 🔗 Child PBIs

- [#NNNN](https://dev.azure.com/<org>/<project>/_workitems/edit/NNNN) — Brief description
- [#NNNN](https://dev.azure.com/<org>/<project>/_workitems/edit/NNNN) — Brief description

## 🪜 Suggested Implementation Order

1. **#NNNN** — Reason this goes first (e.g., "quick win", "foundation for others")
2. **#NNNN** — Reason

---

## 📎 References

| Type | Link |
| --- | --- |
| Requirement | |
| Design doc | |
| Related initiative | |

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     AZURE DEVOPS FIELD: Acceptance Criteria
     (Microsoft.VSTS.Common.AcceptanceCriteria — markdown format)
     Feature-level criteria define when the overall feature can be considered complete.
     ═══════════════════════════════════════════════════════════════════════════ -->

> Each criterion should describe an outcome that is independently verifiable at the feature level.

- [ ] *Criterion describing the primary business or product outcome*
- [ ] *Criterion describing a key cross-cutting or integration expectation*
- [ ] *Criterion describing rollout readiness, adoption, or operational confidence*

---

Template version 1.1 - Dobby Feature Framework
