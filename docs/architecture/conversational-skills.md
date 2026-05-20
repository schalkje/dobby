# Conversational Skills

Conversational skills are standalone, tool-independent skills that drive interactive sessions between the agent and the user. They have no tracker or CLI dependencies — their value comes from the conversation pattern itself.

## The archetype: `grill-me`

`grill-me` is the first conversational skill and defines the pattern for the category:

```yaml
---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching
  shared understanding, resolving each branch of the decision tree.
---
```

### Core behavior

1. **Interrogative loop** — ask questions one at a time, walking down each branch of the decision tree
2. **Recommended answers** — for each question, provide the agent's recommended answer (the user isn't flying blind)
3. **Codebase exploration** — if a question can be answered by reading the code, explore the codebase instead of asking the user
4. **Shared understanding** — continue until all branches are resolved

### Design principles

- **Adversarial but constructive** — the goal is to surface blind spots, not to block
- **Branch-aware** — tracks the decision tree, resolving dependencies between decisions
- **Evidence-based** — prefers codebase evidence over assumptions
- **Finite** — has a natural end state (shared understanding reached)

## Current variations

### `grill-pbi` — Requirements quality gate

**When:** After PBI creation or refinement (suggested by `dobby-ado-create-pbi`, `dobby-ado-update-pbi`, `dobby-gh-create-issue`).

**Focus:** Completeness, clarity, acceptance criteria quality, edge cases, scope boundaries, dependencies. Reads the actual PBI/issue content and compares against the project's templates (`pbi-template.md`, `issue-template.md`).

**Output:** Structured findings with proposed updates. Offers to apply changes via `dobby-update-pbi` or `gh issue edit`.

### `grill-proposal` — Proposal quality gate

**When:** After OpenSpec proposal generation (suggested by `dobby-ado-propose-from-pbi`, `dobby-gh-propose-from-issue`).

**Focus:** Scope alignment with source work item, goals specificity, non-goals coverage, approach justification, feasibility, risks, dependencies, backward compatibility.

**Output:** Structured findings with proposed amendments to `proposal.md`.

### `grill-design` — Design quality gate

**When:** After OpenSpec proposal generation, alongside `grill-proposal` (same suggestion point).

**Focus:** Architecture fit, trade-offs, complexity, error handling, performance, security, testability, migration, task coverage. Grounds every question in the actual codebase.

**Output:** Structured findings with proposed amendments to `design.md` and `tasks.md`.

### Depth strategy (shared across all variations)

Each grill skill supports three depth modes:
- **Quick** (3–5 questions): small, well-scoped items
- **Standard** (5–10 questions): typical items (default)
- **Deep** (exhaustive): large or ambiguous items, cross-cutting concerns

The agent makes an educated guess based on complexity. If unsure, asks the user.

## Creating new variations

Each variation is a **separate skill** with its own `SKILL.md` under `skills/<name>/`. This keeps each variation focused and independently discoverable.

### Variation template

When creating a new conversational skill, use this as a starting structure:

```yaml
---
name: <variation-name>
description: <one-line description including trigger phrases>
---

<Purpose statement — what aspect of the design this variation focuses on>

<Conversation rules — what to ask, how to prioritize, when to stop>

Ask the questions one at a time.

If a question can be answered by exploring the codebase, explore the codebase instead.
```

### What a variation should define

| Element | Purpose | Example |
|---|---|---|
| **Focus area** | What domain or concern lens to apply | Security, cost, accessibility, resilience |
| **Question priorities** | What to ask about first | Attack surfaces before auth flows |
| **Depth triggers** | When to go deeper vs. move on | Go deep on anything user-facing |
| **Exit criteria** | When the session is complete | All identified risks have mitigations |
| **Handoff options** | What to do with the output | Create a PBI, update a proposal, add to design doc |

### Integration with other skills

Conversational skills can be invoked at any point in the workflow:

- **Before creating a PBI** — stress-test the idea before it becomes a work item
- **During refinement** — grill the refined PBI before moving to implementation
- **Before implementation** — critique an OpenSpec proposal before applying it
- **During review** — interrogate design decisions before closing

Integration is **invocation-based**: a tracker or OpenSpec skill can suggest invoking a conversational skill, but they are never called automatically. The user always chooses to enter a grill session.

### Potential future variation ideas

These are illustrative — create variations when a real need arises:

| Variation | Focus | When to use |
|---|---|---|
| Security review | Threat modeling, attack surfaces, data handling | Before implementing auth, API, or data features |
| Cost analysis | Cloud resource costs, scaling implications | When proposing infrastructure changes |
| Incident review | Root cause, timeline, prevention | After an incident, before writing the postmortem |

## What conversational skills are NOT

- **Not automated pipelines** — they are interactive, requiring user participation
- **Not validators** — they surface concerns but don't pass/fail
- **Not tracker-aware** — they don't read or write work items (though their output can feed into tracker skills)
- **Not OpenSpec-aware** — they don't modify spec artifacts (though they can critique them)
