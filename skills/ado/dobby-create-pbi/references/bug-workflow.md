# Creating or Refining a Bug

Contents: [Bug fields](#bug-fields-vs-pbi) · [Bug template](#bug-template) · [Creating a Bug](#creating-a-bug) · [Refining an existing Bug](#refining-an-existing-bug) · [Bug hierarchy](#bug-hierarchy) · [Usage examples](#bug-usage-examples)

Bugs follow the same two-step process as PBIs (create with `az boards`, then update multiline fields via the helper script), but use **different fields and a different template**. All critical rules from the main SKILL.md apply unchanged.

## Bug Fields (vs PBI)

| Field | ADO Reference | Purpose | Template section |
|---|---|---|---|
| Repro Steps | `Microsoft.VSTS.TCM.ReproSteps` | **Primary** content — summary, steps, expected/actual, root cause | First section of `bug-template.md` |
| Description | `System.Description` | **Secondary** — context, environment, related items | Second section of `bug-template.md` |
| Acceptance Criteria | `Microsoft.VSTS.Common.AcceptanceCriteria` | When is the fix verified? | Third section of `bug-template.md` |
| Severity | `Microsoft.VSTS.Common.Severity` | `1 - Critical`, `2 - High`, `3 - Medium`, `4 - Low` | Set via `az boards` `--fields` |
| Priority | `Microsoft.VSTS.Common.Priority` | 1–4 | Set via `az boards` `--fields` |

> ⚠️ For PBIs, the primary content field is `System.Description`. For Bugs, the primary content field is `Microsoft.VSTS.TCM.ReproSteps` — this is what appears prominently in the ADO Bug form.

## Bug Template

Use `templates/bug-template.md` when generating content. The template has three sections separated by HTML comments, mapping to the three multiline fields above. Key differences from the PBI template:

- No user story format (`As a… I want… so that…`)
- Repro Steps is the primary field (includes Summary, Current/Expected Behavior, Steps to Reproduce, Design Reference, Root Cause, Fix Direction)
- Description is secondary (brief context, related items)
- Acceptance Criteria focus on verifying the fix and preventing regression

## Creating a Bug

```bash
# Step 1: Create the Bug (basic fields only)
az boards work-item create \
    --title "<title>" \
    --type "Bug" \
    --project "<project-name>" \
    --area "<area-path>" \
    --iteration "<iteration-path>" \
    --organization "<org-url>" \
    --fields "Microsoft.VSTS.Common.Severity=3 - Medium" "Microsoft.VSTS.Common.Priority=2" \
    --output json

# Step 2: Set multiline fields as Markdown via the helper script
python dobby-create-pbi/scripts/azdo-update-fields.py \
    --work-item-id <id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --field "Microsoft.VSTS.TCM.ReproSteps=<path-to-repro-steps.md>" \
    --field "System.Description=<path-to-description.md>" \
    --field "Microsoft.VSTS.Common.AcceptanceCriteria=<path-to-ac.md>"
```

> ⛔ Same rules as PBIs: **NEVER** pass `--description` on `az boards` for multiline content. **NEVER** write HTML — always Markdown.

## Refining an Existing Bug

When the user asks to "refine" a bug, the workflow is:

1. **Fetch current state**: `az boards work-item show --id <id> --org "<org-url>" -o json`
2. **Extract existing content** from `Microsoft.VSTS.TCM.ReproSteps`, `System.Description`, and `Microsoft.VSTS.Common.AcceptanceCriteria`
3. **Preserve user-provided content**: screenshots (`![alt](attachment-url)`), original observations, and user-added notes must be kept — do not discard them
4. **Enrich with codebase context**: search the repo for relevant design docs, code references, and test specs to add Design Reference, Root Cause, and Fix Direction sections
5. **Generate updated markdown** following `templates/bug-template.md`
6. **Write to temp files and update** via the helper script
7. **Verify** by re-fetching the work item and confirming field lengths are non-zero

## Bug Hierarchy

Bugs follow the same ADO hierarchy rules as PBIs:

| Child type | Valid parent type |
|---|---|
| Bug | Feature (or no parent) |
| Task | Bug |

A Bug's parent must be a Feature — never another Bug or PBI. Use `az boards work-item relation add` to link (not `--parent`).

## Bug Usage Examples

**Refine an existing bug:**
> Refine bug 1013609 based on the repo context

**Create a new bug:**
> Create a bug: "Instance badge is clipped on entity nodes"

**Create from a user report:**
> Create a bug from this: "When I add an entity twice to a diagram, the numbered circle is cut off — I can only see the corner"
