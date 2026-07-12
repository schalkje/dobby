---
name: grill-pbi
description: Stress-test a PBI or issue's requirements, acceptance criteria, and scope. Use after creating or refining a work item, or when the user says "grill this PBI", "review requirements", or "stress-test this issue".
metadata:
  version: "1.0"
---

Stress-test the requirements of a PBI (Azure DevOps) or Issue (GitHub) by interrogating its completeness, clarity, and readiness for implementation.

## Before you start

1. **Identify the work item.** The user should provide or have recently created/updated a PBI or issue. If no work item is in context, ask: "Which PBI or issue should I grill?"

2. **Read the work item content.** Fetch the current title, description, and acceptance criteria:
   - ADO: `az boards work-item show --id <id> --output json`
   - GitHub: `gh issue view <number> --json title,body,labels,milestone`

3. **Read the relevant template** to understand what "good" looks like for this project. The templates ship with the installed `dobby-create-pbi` skill, under its `templates/` folder:
   - ADO PBIs: `dobby-create-pbi/templates/pbi-template.md`
   - ADO Features: `dobby-create-pbi/templates/feature-template.md`
   - GitHub Issues: `dobby-create-pbi/templates/issue-template.md`
   (Only the installed scenario's templates exist — use whichever is present.)

4. **Choose depth.** Make an educated guess based on the work item's complexity:
   - **Quick** (3–5 questions): small, well-scoped items with clear acceptance criteria
   - **Standard** (5–10 questions): typical PBIs, most items land here
   - **Deep** (exhaustive): large or ambiguous items, cross-cutting concerns, items touching many systems
   
   If unsure, ask the user: "This looks moderately complex — shall I do a standard review (5–10 questions) or go deep?"

## The interrogation

Ask questions **one at a time**. For each question, provide your recommended answer based on what you've read.

### What to probe

- **Completeness** — Are all template sections filled in? Are there gaps?
- **Clarity** — Would a developer unfamiliar with the context understand what to build?
- **Acceptance criteria** — Are they specific, testable, and unambiguous? Do they cover the happy path AND edge cases?
- **Scope** — Is the scope well-bounded? Are there implicit assumptions that should be explicit?
- **Dependencies** — Are external dependencies, prerequisites, or blockers identified?
- **Edge cases** — What happens with empty inputs, large datasets, concurrent access, permissions?
- **Non-goals** — What is explicitly out of scope? (Prevents scope creep)
- **User impact** — Who is affected? Is the user story clear?

### Rules

- If a question can be answered by exploring the codebase, explore the codebase instead of asking the user.
- Don't ask questions the work item already answers clearly.
- Prioritize questions by risk — ask about the most likely failure points first.
- Stop when no blocking ambiguities remain or when you've reached the selected depth.

## After the interrogation

Produce a structured summary:

```markdown
## Grill Findings — PBI #<id>

### Required updates (blocking)
- <issues that would cause implementation problems if not addressed>

### Suggested updates (improvements)
- <improvements that would strengthen the work item but aren't blocking>

### Open decisions
- <questions that surfaced but need stakeholder input>

### Proposed changes
<concrete additions or changes to the description and/or acceptance criteria>
```

Then ask: **"Do you want me to apply these updates to the PBI/issue?"**

If yes, follow the appropriate update path:
- ADO: read and follow the `dobby-update-pbi` skill's SKILL.md with the proposed changes
- GitHub: use `gh issue edit <number> --body-file <file>` with the updated body
