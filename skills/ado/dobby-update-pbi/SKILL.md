---
name: dobby-update-pbi
description: Updates/refines a PBI, Bug, or Feature in Azure DevOps. Updates multiline fields (Description, Acceptance Criteria, Repro Steps) via the helper script to ensure Markdown format. Supports a refinement mode that synthesizes description, comments, and codebase context into a well-structured PBI.
metadata:
  author: dobby
  version: "2.0"
---

Update or refine an existing work item (PBI, Bug, or Feature) in Azure DevOps.


This skill has two modes:

| User intent | Mode | What happens |
|---|---|---|
| "Update PBI 123 title to …" | **Field update** | Directly changes the specified fields |
| "Set acceptance criteria to …" | **Field update** | Directly changes the specified fields |
| "Refine PBI 123" | **Refinement** | Reads everything (fields, comments, codebase), synthesizes a well-structured PBI |
| "Improve this PBI" | **Refinement** | Same as above |
| "Make PBI 123 clearer" | **Refinement** | Same as above |
| "Build a good PBI from 123" | **Refinement** | Same as above |

If the intent is ambiguous, ask the user: "Do you want to update specific fields, or do a full refinement?"

## ⛔ Critical Rules (read before every run)

1. **NEVER use `--description` on `az boards work-item update`.** It truncates at the first newline. Always use the helper script (`azdo-update-fields.py`) for multiline fields.
2. **NEVER write HTML in description, acceptance criteria, or repro steps fields.** Content must be **Markdown** — not HTML. No `<b>`, `<br>`, `<ul>`, `<li>` tags. Use markdown syntax: `**bold**`, line breaks, `- list items`. The helper script sets the field format to Markdown; HTML content in a Markdown-formatted field renders as raw escaped tags.
3. **Follow the template** when generating content. PBIs use `skills/ado/dobby-create-pbi/templates/pbi-template.md`; Bugs use `skills/ado/dobby-create-pbi/templates/bug-template.md`. When updating a single section, preserve existing content in other sections unless the user explicitly asks to replace everything.
4. **Always use the helper script for multiline fields** — `az boards` cannot set markdown format.
5. **Run commands exactly as shown — no piping, no post-processing.** Every `az` and `python` command in this skill is designed to be run standalone with `--output json`. Do NOT append any pipe (`|`) to transform, filter, or format the output. This includes `| ConvertFrom-Json`, `| Select-Object`, `| jq`, `| python -c "..."`, `| grep`, or any other pipe. Read the full JSON output and extract fields in your own reasoning.
6. **Use canonical `skills/` paths for all file reads and script invocations.** This SKILL.md lives at `skills/dobby-update-pbi/`. Reference scripts and templates from this canonical path — e.g., `python skills/_lib/azdo-get-comments.py`, not from `.github/skills/` or `.claude/skills/` host copies. The host copies are auto-generated mirrors and must not be referenced directly.

## Field Mapping by Work Item Type

| Work Item Type | Primary content field | Other multiline fields |
|---|---|---|
| **Product Backlog Item** | `System.Description` | `Microsoft.VSTS.Common.AcceptanceCriteria` |
| **Bug** | `Microsoft.VSTS.TCM.ReproSteps` | `System.Description`, `Microsoft.VSTS.Common.AcceptanceCriteria` |
| **Feature** | `System.Description` | `Microsoft.VSTS.Common.AcceptanceCriteria` |

---

## Common Steps (both modes)

### 1. Validate Prerequisites

Run these checks (same as create skill):

**1a. Check Azure CLI and extension**
```bash
az version --output json
```
- If `az` is not found → stop: "Azure CLI is not installed."
- If `azure-devops` is not listed under `extensions` → install it: `az extension add --name azure-devops`

**1b. Check Python availability**
```bash
python --version
```
- If `python` is not found → stop: "Python 3 is required for the markdown field helper script."

**1c. Check authentication**
```bash
az account show --query "{user:user.name, tenant:tenantId}" --output json
```
- If this fails → stop: "Run: `az login`"

### 2. Load Configuration

Read `.dobby/config.json` to get `organization` and `project`.

### 3. Fetch Current Work Item

```bash
az boards work-item show --id <work-item-id> --organization "<org-url>" --expand Relations --output json
```

Extract:
- **Type**: `fields["System.WorkItemType"]` — determines which fields and template to use
- **Title**: `fields["System.Title"]`
- **Current field values** — so you can preserve content the user didn't ask to change
- **Relations** — parent, children, related items (used in refinement mode)

Display current title and type to the user for confirmation.

**Then choose the mode** based on the user's intent (see mode table above).

---

## Field Update Mode (steps 4–8)

Use this mode when the user wants to change specific, known fields.

### 4. Determine What to Update

Based on the user's request, determine which fields need updating:

**Simple fields** (title, area path, iteration, priority, state):
- Use `az boards work-item update --fields "Field=value"` directly.

**Multiline fields** (Description, Acceptance Criteria, Repro Steps):
- Must use the helper script (step 5).
- When updating a subset of the content (e.g., "add acceptance criteria"), fetch current content and merge intelligently — don't overwrite content the user didn't mention.

### 5. Update Multiline Fields via Helper Script

Write the markdown content to temporary files, then run the helper script:

```bash
python skills/_lib/azdo-update-fields.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --field "System.Description=<path-to-desc.md>" \
    --field "Microsoft.VSTS.Common.AcceptanceCriteria=<path-to-ac.md>"
```

For **Bugs**, use the appropriate field for the primary content:
```bash
python skills/_lib/azdo-update-fields.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --field "Microsoft.VSTS.TCM.ReproSteps=<path-to-reprosteps.md>" \
    --field "Microsoft.VSTS.Common.AcceptanceCriteria=<path-to-ac.md>"
```

The script:
- Authenticates automatically (PAT via `AZURE_DEVOPS_EXT_PAT`, bearer via `ADO_TOKEN`, or `az account get-access-token`)
- Sets both the field content and the field format to Markdown in one API call
- Is idempotent — safe to re-run on failure
- Uses `op: add` (upsert-safe)

**Clean up temporary files after successful update.**

### 6. Update Simple Fields (if any)

```bash
az boards work-item update --id <work-item-id> \
    --fields "System.Title=<new-title>" \
    --organization "<org-url>" \
    --output json
```

### 7. Verify the Update

```bash
az boards work-item show --id <work-item-id> --organization "<org-url>" --output json
```

Confirm the updated fields have the expected content. Report the work item URL to the user.

### 8. Add Comment (optional)

If the update includes context that should be preserved as a comment (e.g., analysis notes, screenshots, evidence), add it:

```bash
az boards work-item update --id <work-item-id> \
    --discussion "<comment-text>" \
    --organization "<org-url>" \
    --output json
```

Note: `--discussion` is fine for comments — they are plain text/markdown and don't have the truncation issue.

---

## Refinement Mode (steps R1–R7)

Use this mode when the user says "refine", "improve", or wants a well-structured PBI built from all available context. This mode reads everything — description, acceptance criteria, discussion comments, parent context, and the codebase — then synthesizes a complete, template-compliant PBI.

### R1. Fetch Discussion Comments

Fetch the work item's discussion thread using the helper script:

```bash
python skills/_lib/azdo-get-comments.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --max-comments 50
```

The script returns JSON with each comment's `author`, `date`, and `text`.

**⚠️ How to treat comments:**

Comments are **historical context and ideas** — they are NOT authoritative requirements. They may contain:
- Brainstorming and early ideas (not all will be relevant)
- Current state observations (may be outdated)
- Stakeholder feedback (valuable but may conflict with other comments)
- Technical notes and investigation results
- Rejected approaches (still useful as context for what NOT to do)

**Rules for using comments:**
- Prefer the current PBI fields and explicit user instructions over comment content
- If comments conflict with each other, surface the conflict and ask the user
- If comments conflict with the current PBI description, ask — don't silently choose
- Extract useful information (requirements hints, edge cases, stakeholder preferences) but don't treat every comment as a requirement
- Preserve author attribution when referencing specific comment insights
- Recent comments generally carry more weight than older ones, but use judgment

### R2. Fetch Parent Context (bounded)

Check the work item's relations (from step 3) for a parent link. If found:

```bash
az boards work-item show --id <parent-id> --organization "<org-url>" --output json
```

Extract the parent's title, type (Feature/Epic), and description summary. This provides the broader context for the PBI — what business goal it serves.

**Direct children** (if any): fetch titles and states for up to 5 children. If more, summarize the count. Children are context only — they don't define the current PBI's requirements.

### R3. Explore the Codebase

Search the repository for context relevant to the PBI. Use the title, description, and comment insights to guide the search:

- Look for existing code, modules, or services mentioned in the PBI or comments
- Find relevant documentation, design docs, or test specs
- Identify existing patterns and conventions in the affected areas
- Surface hidden complexity (e.g., the PBI says "remove field X" but X is used in 12 places)

**Guardrails:**
- Search based on specific terms from the PBI, not broad exploration
- Prefer existing docs/tests/code near matching features
- Do not infer product requirements solely from current implementation — code is how it IS, not how it SHOULD be
- If code contradicts the PBI or comments, present the discrepancy to the user
- Keep exploration bounded — spend at most a few minutes, then move on

### R4. Read the Template

Read the appropriate template to guide the output structure:

- PBIs: `skills/ado/dobby-create-pbi/templates/pbi-template.md`
- Bugs: `skills/ado/dobby-create-pbi/templates/bug-template.md`
- Features: `skills/ado/dobby-create-pbi/templates/feature-template.md`

The template defines the expected sections and structure. The refined PBI must follow this structure.

### R5. Synthesize the Refined PBI

Combine all gathered context into a well-structured PBI:

**Inputs (in priority order):**
1. Explicit user instructions (highest priority)
2. Current PBI description and acceptance criteria
3. Parent work item context (business goal)
4. Codebase findings (technical reality)
5. Discussion comments (ideas and context — weigh, don't blindly include)

**Produce two separate outputs:**
1. **Proposed Description** (`System.Description`) — following the template structure
2. **Proposed Acceptance Criteria** (`Microsoft.VSTS.Common.AcceptanceCriteria`) — specific, testable, Given/When/Then format

**What the refinement should do:**
- Fill in empty or incomplete template sections with information from comments and codebase
- Sharpen vague language into specific, actionable requirements
- Add scope boundaries (in-scope / out-of-scope) if not already present
- Add dependencies if discovered during codebase exploration
- Convert scattered comment ideas into structured acceptance criteria where appropriate
- Preserve any existing content that is already well-written — don't rewrite for the sake of it
- Convert HTML to Markdown if the existing content is in HTML format

**What the refinement should NOT do:**
- Invent requirements not supported by any input (description, comments, or user instructions)
- Silently resolve conflicts between comments — ask the user
- Remove content unless it's clearly wrong or outdated (and flag the removal)

### R6. Present the Proposed Refinement

Show the user the full proposed refinement before applying:

```markdown
## Proposed Refinement — PBI #<id>: "<title>"

### Sources used
- Description: <existing / empty / HTML-converted>
- Acceptance Criteria: <existing / empty>
- Comments: <N> comments from <date-range> (<M> found relevant)
- Parent: <parent title> (or "none")
- Codebase: <summary of what was found>

### Assumptions made
- <any assumptions that weren't explicitly stated>

### Unresolved questions
- <conflicts or ambiguities that need user input>

---

### Proposed Description
<full proposed description following template structure>

---

### Proposed Acceptance Criteria
<full proposed acceptance criteria in Given/When/Then format>
```

**If there are unresolved questions**, ask them now and incorporate the answers before proceeding.

Then ask: **"Do you want me to apply this refinement to the PBI?"**

### R7. Apply the Refinement

On user approval, apply using the same helper script as field update mode (step 5):

```bash
python skills/_lib/azdo-update-fields.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --field "System.Description=<path-to-desc.md>" \
    --field "Microsoft.VSTS.Common.AcceptanceCriteria=<path-to-ac.md>"
```

After successful update, verify (same as step 7) and report the work item URL.

---

## Content Guidelines

- **All content must be Markdown — never HTML.** No exceptions.
- Use the template from `skills/ado/dobby-create-pbi/templates/` as the structural guide.
- When partially updating (e.g., only acceptance criteria), don't touch other fields.
- When replacing a field entirely, follow the template structure for that field.
- When the existing content is in HTML format (legacy), convert it to Markdown during the update — this fixes the format going forward.

## Error Handling

- If the helper script fails → report the error and provide the manual retry command.
- If the work item doesn't exist → stop and report.
- If the user doesn't have permissions → stop and suggest checking access.
- If the comments script fails → warn but continue refinement with available context (description only). Comments are valuable but not essential.

## Optional Quality Gate

After a successful update or refinement, suggest:

> **Optional:** Run `grill-pbi` to stress-test the refined requirements and acceptance criteria before moving to proposal generation.

Do not invoke `grill-pbi` automatically — only suggest it. The user decides whether to grill.

## Efficiency Notes

- Skip prerequisite checks if they were already validated in the same session (e.g., during a create-then-update flow).
- Batch all field updates into a single helper script call when possible.
- Don't prompt for fields the user already provided.
