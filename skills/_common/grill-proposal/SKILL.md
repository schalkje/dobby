---
name: grill-proposal
description: Stress-test an OpenSpec proposal's scope, goals, and feasibility. Use after generating a proposal from a PBI/issue, or when the user says "grill this proposal", "review the proposal", or "challenge the scope".
metadata:
  version: "1.0"
---

Stress-test an OpenSpec proposal by interrogating its scope, goals, non-goals, approach choice, and feasibility.

<!-- dobby:include:minimal-context-review -->

## Before you start

1. **Identify the change.** The user should name or have recently generated an OpenSpec change. If no change is in context, check:
   ```bash
   openspec list --json
   ```
   If only one active change exists, use it. If ambiguous, ask: "Which change should I grill?"

2. **Read the proposal.** Read `openspec/changes/<name>/proposal.md` thoroughly.

3. **Read the source work item** (if the proposal was generated from a PBI/issue). Look for the traceability line in `proposal.md`:
   - ADO: `> Source: Azure DevOps PBI [#<id>](<url>)`
   - GitHub: `> Source: GitHub Issue [#<id>](<url>)`
   
   If found, fetch the original work item to compare scope alignment:
   - ADO: `az boards work-item show --id <id> --output json`
   - GitHub: `gh issue view <number> --json title,body`

4. **Choose depth.** Make an educated guess:
   - **Quick** (3–5 questions): small, focused proposals with clear scope
   - **Standard** (5–10 questions): typical proposals
   - **Deep** (exhaustive): proposals touching multiple systems, large refactors, or new subsystems
   
   If unsure, ask the user.

## The interrogation

Ask questions **one at a time**. For each question, provide your recommended answer.

### What to probe

- **Scope alignment** — Does the proposal match the source work item? Is it too broad or too narrow?
- **Goals** — Are the goals specific and measurable? Will you know when you're done?
- **Non-goals** — Are important exclusions called out? What's being deferred?
- **Approach choice** — Why this approach over alternatives? What was considered and rejected?
- **Feasibility** — Can this realistically be implemented? Are there technical unknowns?
- **Risks** — What could go wrong? What assumptions are being made?
- **Dependencies** — Does this depend on other changes, services, or teams?
- **Incremental value** — Can this be broken into smaller deliverables? Is the first milestone clear?
- **Backward compatibility** — Does this break existing behavior? Is migration needed?

### Rules

- If a question can be answered by exploring the codebase, explore the codebase instead of asking the user.
- Compare against the source PBI/issue to catch scope drift.
- Don't re-interrogate what grill-pbi already covered (requirements-level concerns). Focus on the "what and why" of the proposed approach.
- Stop when no blocking ambiguities remain or when you've reached the selected depth.

## After the interrogation

Produce a structured summary:

```markdown
## Grill Findings — Proposal "<change-name>"

### Required updates (blocking)
- <issues that would cause the proposal to fail or drift from intent>

### Suggested updates (improvements)
- <improvements to scope definition, risk identification, or approach justification>

### Open decisions
- <questions that need stakeholder or architect input>

### Proposed amendments to proposal.md
<concrete additions or changes — quote existing text and show the amendment>
```

Then ask: **"Do you want me to apply these amendments to the proposal?"**

If yes, edit `openspec/changes/<name>/proposal.md` directly with the agreed changes.
