---
name: dobby-gh-propose-from-issue
description: Internal — creates an OpenSpec proposal from a GitHub Issue. Invoked by dobby-propose-from-pbi after backend resolution. Do not invoke directly unless forcing the GitHub backend. Fetches issue details and generates proposal, design, and task artifacts ready for implementation.
metadata:
  author: dobby
  version: "1.0"
---

<!-- This file is a copy of `skills/dobby-gh-propose-from-issue/SKILL.md` — edit the source, not this copy. Regenerate with `python scripts/sync-skills.py`. -->

Create an OpenSpec change proposal from an existing GitHub Issue.

This skill is the **GitHub implementation** invoked by the `dobby-propose-from-pbi` dispatcher after it resolves `backend: "github"` from `.dobby/config.json`. Direct invocation is supported as an escape hatch.

**Input**: An issue identifier — issue number, title/keywords, `#42` reference, or a full GitHub issue URL.

## Defaults

Read the `github` block from `.dobby/config.json` for `owner` and `repo`. If missing, prompt and persist as in `dobby-gh-create-issue`.

## Steps

### 1. Validate Prerequisites

**1a. Check gh CLI**
```bash
gh --version
```
- If `gh` is not found → stop: "GitHub CLI is not installed."

**1b. Check OpenSpec CLI**
```bash
openspec --version
```
- If `openspec` is not found → stop: "OpenSpec CLI is required. Install it first."

**1c. Check authentication**
```bash
gh auth status
```
- If not authenticated → stop: "Run: `gh auth login`"
- Display the active GitHub user.

### 2. Resolve Owner and Repo

Read from `.dobby/config.json` `github` block. Prompt for missing values and validate access:
```bash
gh repo view "<owner>/<repo>" --json name,owner --output json
```

### 3. Find the Issue

Parse the user's input to determine the lookup strategy:

| Input format | Strategy |
|---|---|
| Numeric ID (e.g., `42`) | Direct fetch |
| `#42` | Strip `#`, fetch by ID |
| GitHub issue URL | Extract number from path, fetch |
| Title or keywords | Search via `gh issue list --search` |

**3a. Direct fetch by ID**
```bash
gh issue view <N> --repo "<owner>/<repo>" --json number,title,state,body,labels,milestone,url,assignees
```
- If the issue is not found → stop: "Issue #<N> does not exist or is not accessible in <owner>/<repo>."

**3b. Search by title/keywords**
```bash
gh issue list --repo "<owner>/<repo>" --search "<keywords>" --state all --json number,title,state,url --limit 10
```
- Sort by relevance (gh's default).
- If multiple matches → present a selection list with number, title, and state. Ask the user to confirm.
- If no matches → suggest broadening the search or entering an issue number directly.

### 4. Extract Issue Details

From the fetched issue, extract these fields:

| Field | Used as |
|---|---|
| `title` | Title of the OpenSpec change |
| `body` | Primary source content for proposal/design/specs |
| `labels` | Hints for capability identification, scope tagging |
| `milestone` | Optional context for prioritization / scope |
| `assignees` | Stakeholder context |
| `state` | If `closed`, warn before proceeding |
| `url` | Source traceability link |

**Body content**: GitHub issue bodies are already markdown — no HTML normalization is required. Preserve the existing structure (Description / Acceptance Criteria sections, etc.) when injecting into the spec artifacts.

**If the body is empty**, warn the user:
> "This issue has no body. I can still generate a proposal, but the spec will be based on the title alone. Want to continue, or add content to the issue first?"

**If the issue is closed**, ask before proceeding:
> "Issue #<N> is closed. Do you still want to generate a spec for it?"

### 5. Fetch Related Context (bounded)

**5a. Linked PRs** (optional)

Check for any PRs that reference this issue:
```bash
gh api "repos/<owner>/<repo>/issues/<N>/timeline" --jq '[.[] | select(.event=="cross-referenced") | .source.issue | select(.pull_request) | {number: .number, title: .title, state: .state}]'
```
Include as "Existing implementation context" if PRs exist.

**5b. Sub-issues via task-list references** (optional, capped)

GitHub doesn't have a first-class sub-issue concept, but task-list references in the body act as one. Parse `- [ ] #<N>` lines from the issue body:
- For each referenced issue (cap at 5), fetch title and state.
- Include as "Related items" in the spec context.

**5c. Linked issues** (optional, capped)

Search for issues that reference this one in their body:
```bash
gh issue list --repo "<owner>/<repo>" --search "#<N>" --state all --json number,title,state --limit 5
```
Include as context only.

### 6. Refine the Issue

Before generating the spec, analyze the issue for gaps, ambiguities, or missing details.

**6a. Identify gaps**

Review the issue body, labels, and any related context gathered in steps 4-5. Look for:
- Ambiguous scope
- Missing behavioral decisions
- Edge cases not covered in acceptance criteria
- Implicit assumptions that should be explicit

**6b. Ask refinement questions**

Present refinement questions to the user using a structured form. Group related questions logically. Provide sensible defaults where possible.

**6c. Write refinements back to the issue**

After the user answers (or after making reasonable decisions if running autonomously), update the issue body in GitHub with the refined content. Use a temp file to avoid quoting issues:

```bash
gh issue edit <N> --repo "<owner>/<repo>" --body-file <path-to-updated-body.md>
```

Append a "Refinement Notes" section to the body capturing the decisions and rationale. This keeps the issue as the source of truth.

### 7. Confirm Before Generating

Present a summary of what will be used to generate the spec:

```
## Proposal Context

- **Issue**: #<N> — "<title>" [<state>]
- **Repo**: <owner>/<repo>
- **Description**: <summary or "empty">
- **Acceptance Criteria**: <count> criteria (including refinements)
- **Labels**: <comma-separated>
- **Related**: <N> items included as context
- **Proposed change name**: issue-<N>-<title-slug>
- **Refinements applied**: <count> questions answered, issue updated

Proceed?
```

Wait for user confirmation.

### 8. Create OpenSpec Change

**8a. Derive change name**

Generate a kebab-case name from the issue:
- Format: `issue-<N>-<title-slug>` (e.g., `issue-42-add-dark-mode-toggle`).
- Truncate the title slug at a word boundary if the full name would exceed ~50 characters.

**Check for existing change**:
- If `openspec/changes/<name>/` already exists, ask:
  1. Continue/update that change
  2. Create with a different name
  3. Abort

**8b. Create the change**
```bash
openspec new change "<name>"
```

**8c. Get artifact build order**
```bash
openspec status --change "<name>" --json
```
Parse the JSON for `applyRequires` and the list of artifacts with their dependencies.

**8d. Generate artifacts in dependency order**

Loop through artifacts whose dependencies are satisfied:

1. Get instructions:
   ```bash
   openspec instructions <artifact-id> --change "<name>" --json
   ```

2. Read any completed dependency artifact files for context.

3. **Inject issue context**: Use the fetched issue details as the primary input:
   - **proposal.md**: Issue title as the change title, body description as problem/motivation, acceptance criteria as success criteria.
   - **design.md**: Acceptance criteria and body inform design decisions and constraints.
   - **specs/**: Map acceptance criteria and labels to capability specs.
   - **tasks.md**: Break down acceptance criteria into implementable tasks.

4. Use the `template` from instructions as the structure. Apply `context` and `rules` as constraints — do NOT copy them into the output.

5. Write the artifact file to `outputPath`.

6. Re-check status; continue until all `applyRequires` artifacts are complete.

### 9. Add Traceability

**9a. Record source in proposal.md**

Include a "Source" line at the top of `proposal.md`:

```markdown
> Source: GitHub Issue [#<N>](<issue-url>) — "<title>"
```

This makes the link durable regardless of whether the issue is updated later.

**9b. Offer to link back to the issue** (opt-in)

After successful spec creation, ask:
> "Would you like me to add a comment to issue #<N> linking to this OpenSpec change?"

If yes, post a comment via `gh`:
```bash
gh issue comment <N> --repo "<owner>/<repo>" --body "OpenSpec change created: \`<change-name>\`. Artifacts: proposal.md, design.md, tasks.md."
```

Do not update automatically — respect team conventions.

### 10. Show Final Status

```bash
openspec status --change "<name>"
```

Present a summary:

```
## ✓ OpenSpec Proposal Created from Issue #<N>

- **Change**: <change-name>
- **Location**: openspec/changes/<change-name>/
- **Artifacts created**:
  - proposal.md — what & why
  - design.md — how
  - specs/ — capability specs
  - tasks.md — implementation steps
- **Source Issue**: #<N> — "<title>"

Ready for implementation! Invoke `/openspec-apply-change <name>` or ask me to implement.
```

## Error Handling

- **Wrong identity**: `gh auth status` shows the wrong account → suggest `gh auth switch`.
- **Issue not found**: clear message with the ID/keywords used.
- **Issue inaccessible**: suggest checking repo permissions or visibility scope.
- **Empty issue body**: warn and ask for additional context before generating.
- **Search failures**: retry with a broader query if needed.
- **OpenSpec CLI failure**: report the failing command and suggest manual retry.
- **Partial success**: if some artifacts are created but not all, report what succeeded and what failed. The user can re-run artifact generation.
- **Issue update failure**: report partial success — the spec is created, only the issue link failed.

## Guardrails

- Always show the logged-in GitHub identity early.
- Do not hard-code label or milestone semantics — let the user's content drive the spec.
- Include the issue number in the change name for traceability.
- Bound related-item fetching — cap at 5 per category.
- Do not update the issue automatically — always ask first.
- Use `--output json` or `--json` on `gh` commands for reliable parsing.
- Include `--repo "<owner>/<repo>"` on all `gh` commands.

## Usage Examples

**By issue number:**
> Create a spec for issue 42

**By #N reference:**
> Spec from #42

**By URL:**
> Create a spec for https://github.com/myorg/myrepo/issues/42

**By title/keywords:**
> Create a spec for the "dark mode toggle" issue

**Minimal:**
> Spec from issue 42
