---
name: grill-design
description: Stress-test an OpenSpec design's architecture, trade-offs, and implementation risks. Use after generating a design, or when the user says "grill this design", "review the architecture", or "challenge the design".
metadata:
  version: "1.0"
---

<!-- This file is a copy of `skills/grill-design/SKILL.md` — edit the source, not this copy. Regenerate with `python scripts/sync-skills.py`. -->

Stress-test an OpenSpec design by interrogating its architecture, implementation strategy, trade-offs, and risks.

## Before you start

1. **Identify the change.** The user should name or have recently generated an OpenSpec change. If no change is in context, check:
   ```bash
   openspec list --json
   ```
   If only one active change exists, use it. If ambiguous, ask: "Which change's design should I grill?"

2. **Read the design artifacts.** Read these files from `openspec/changes/<name>/`:
   - `design.md` — the primary target
   - `proposal.md` — for context on goals and scope
   - `tasks.md` — to understand the planned implementation breakdown

3. **Explore the affected codebase.** Based on what the design describes:
   - Find the files, modules, or services that will be modified
   - Understand existing patterns, conventions, and dependencies
   - Identify integration points and potential conflict areas

4. **Choose depth.** Make an educated guess:
   - **Quick** (3–5 questions): small, contained changes in a well-understood area
   - **Standard** (5–10 questions): typical designs
   - **Deep** (exhaustive): architectural changes, new subsystems, changes crossing module boundaries
   
   If unsure, ask the user.

## The interrogation

Ask questions **one at a time**. For each question, provide your recommended answer grounded in what you found in the codebase.

### What to probe

- **Architecture fit** — Does this design align with existing patterns? Does it introduce inconsistency?
- **Trade-offs** — What is being traded for what? Are the trade-offs acknowledged and justified?
- **Complexity** — Is this simpler than it needs to be (missing cases) or more complex (over-engineering)?
- **Error handling** — What happens when things go wrong? Are failure modes addressed?
- **Performance** — Are there scaling concerns? N+1 queries, unbounded loops, large payloads?
- **Security** — Are there auth, input validation, or data exposure concerns?
- **Testability** — Can this design be tested effectively? Are the boundaries clear?
- **Migration** — Does existing data or state need migrating? Is rollback possible?
- **Task breakdown** — Do the tasks in `tasks.md` cover the full design? Are any steps missing?
- **Alternative approaches** — Was a simpler approach considered? Why was this one chosen?

### Rules

- **Ground every question in the codebase.** Don't ask generic architecture questions — point to specific files, patterns, or code that relates to your concern.
- Don't re-interrogate scope or goals (that's `grill-proposal`'s job). Focus on the "how."
- Prioritize questions by implementation risk — ask about the most likely technical pitfalls first.
- Stop when no blocking ambiguities remain or when you've reached the selected depth.

## After the interrogation

Produce a structured summary:

```markdown
## Grill Findings — Design "<change-name>"

### Required updates (blocking)
- <design gaps that would cause implementation failures or architectural problems>

### Suggested updates (improvements)
- <improvements to design clarity, risk mitigation, or pattern consistency>

### Open decisions
- <technical decisions that need further investigation or team input>

### Proposed amendments to design.md
<concrete additions or changes — quote existing text and show the amendment>

### Task coverage
<any tasks that should be added, removed, or reordered in tasks.md>
```

Then ask: **"Do you want me to apply these amendments to the design and tasks?"**

If yes, edit `openspec/changes/<name>/design.md` and optionally `tasks.md` with the agreed changes.
