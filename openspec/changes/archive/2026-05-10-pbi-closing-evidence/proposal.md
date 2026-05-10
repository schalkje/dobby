## Why

When a developer closes a PBI or task in Azure DevOps, there is no structured way to capture evidence of the work done. Stakeholders and reviewers need visual proof—screenshots, before/after comparisons, and descriptive notes—to verify that changes meet requirements. Without this, closed items lack traceability and the team loses confidence in what was delivered.

## What Changes

- Introduce an automated evidence-gathering step when closing a PBI or task
- Capture "before" screenshots proactively (when feasible) so that a meaningful before/after comparison can be presented at closing time
- Post a closing comment on the Azure DevOps work item containing markdown-formatted text and embedded images
- Store all evidence in the work item's comment stream so it is co-located with the item and easily discoverable

## Capabilities

### New Capabilities
- `closing-evidence`: Collect, format, and post evidence (screenshots, markdown description) as a comment when closing a work item
- `before-capture`: Proactively capture "before" state screenshots so they are available for comparison at closing time

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- Azure DevOps Work Items API: will use the comments/discussion endpoint to post rich markdown with embedded images
- Image storage: images need to be uploaded to a location reachable from Azure DevOps comments (e.g., Azure DevOps attachments API)
- Developer workflow: adds an interactive step during task/PBI closure to gather and confirm evidence before posting
- No breaking changes to existing systems
