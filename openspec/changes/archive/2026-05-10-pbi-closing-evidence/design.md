## Context

Dobby is an agentic DevOps assistant for Azure DevOps. One of its core workflows is assisting developers during the implementation stage—specifically when closing tasks and PBIs. Currently there is no mechanism to capture evidence of completed work. Developers close items without attaching proof, making it hard for POs and reviewers to verify delivery.

Azure DevOps work items support a comment/discussion thread that accepts HTML (and thus markdown-rendered content). Images can be attached to work items via the Attachments API and referenced inline in comments. This is the natural place to store evidence.

## Goals / Non-Goals

**Goals:**
- Provide an interactive closing flow that gathers evidence (screenshots, text descriptions) before marking a work item as Done
- Post a well-formatted markdown comment on the work item summarizing the change with embedded images
- Support capturing "before" state early so before/after comparisons are available at closing time
- Upload images via the Azure DevOps Attachments API so they are permanently linked to the work item

**Non-Goals:**
- Automated screenshot capture (e.g., browser automation)—the developer provides screenshots manually
- Video evidence or screen recordings
- Modifying work item fields beyond state and comments (no custom fields)
- Building a standalone UI—this operates through the Copilot / CLI interaction model

## Decisions

### 1. Store evidence in work item comments (not a wiki or external storage)

**Decision**: Post evidence as a comment on the Azure DevOps work item.

**Rationale**: Comments are co-located with the item, visible to all team members, and preserved in the item's history. External storage (wiki pages, blob storage) would require cross-linking and risks orphaned content.

**Alternatives considered**:
- Wiki page per PBI: harder to discover, extra navigation
- Linked git commit with screenshots: not all evidence relates to code changes

### 2. Use Azure DevOps Attachments API for images

**Decision**: Upload images via the Work Item Tracking Attachments API, then embed the returned URL in the markdown comment.

**Rationale**: This keeps images within the Azure DevOps project, respects access controls, and avoids external hosting dependencies.

### 3. Before-capture is an explicit opt-in step

**Decision**: Provide a separate `before-capture` command/step that the developer triggers before starting work. The captured images are stored locally (in a session or temp directory) until closing time.

**Rationale**: Not all changes need before/after comparisons. Making it opt-in avoids unnecessary overhead while keeping the capability available.

### 4. Markdown comment format

**Decision**: Use a structured markdown template for the closing comment:
- Header with work item ID and title
- "What changed" text section
- "Before" images (if captured)
- "After" images
- Developer notes

**Rationale**: A consistent format makes evidence scannable across items and sets a team standard.

## Risks / Trade-offs

- **[Image size limits]** → Azure DevOps has attachment size limits. Mitigation: validate file size before upload and warn the developer.
- **[Before-capture forgotten]** → Developer may forget to capture "before" state. Mitigation: prompt at closing time if no before images exist; this is informational, not blocking.
- **[API permissions]** → The agent needs write access to work item comments and attachments. Mitigation: validate permissions early and surface clear error messages.
- **[Markdown rendering in ADO]** → Azure DevOps renders a subset of markdown/HTML in comments. Mitigation: test comment format against ADO's rendering and keep to supported elements.
