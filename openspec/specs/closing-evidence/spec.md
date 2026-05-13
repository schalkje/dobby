# closing-evidence Specification

## Purpose

Define how the dobby skill chain posts implementation evidence (markdown summary plus before/after screenshots) on an Azure DevOps work item when the developer closes a PBI or task. Covers comment composition, image upload via the ADO Attachments API, and the interactive evidence-gathering flow. Applies to the ADO-backed closing chain — GitHub-backed projects use a different evidence vehicle (see `github-issue-closing`).
## Requirements
### Requirement: Post closing evidence comment
The `dobby-ado-close-pbi` skill SHALL post a markdown-formatted comment on the Azure DevOps work item when a developer closes a PBI or task. The comment SHALL contain a structured summary of the change including text description and embedded images. This skill SHALL be invoked only by the `dobby-close-pbi` dispatcher when the project's active backend (per `.dobby/config.json`) is `"ado"`.

#### Scenario: Close work item with text and screenshots
- **WHEN** the developer initiates the close flow for a work item and provides a text description and one or more "after" screenshots
- **THEN** the system uploads the images via the Azure DevOps Attachments API, composes a markdown comment with the description and embedded images, posts the comment to the work item's discussion thread, and sets the work item state to Done

#### Scenario: Close work item with before and after images
- **WHEN** the developer initiates the close flow and both "before" and "after" images are available
- **THEN** the closing comment SHALL include a "Before" section with the before images and an "After" section with the after images, enabling visual comparison

#### Scenario: Close work item with text only
- **WHEN** the developer initiates the close flow and provides only a text description without screenshots
- **THEN** the system SHALL post the markdown comment with the text description and no image sections

#### Scenario: Dispatcher routes to this skill when backend is ADO
- **WHEN** the user invokes `dobby-close-pbi` and `.dobby/config.json` has `backend: "ado"`
- **THEN** the dispatcher SHALL Read `skills/dobby-ado-close-pbi/SKILL.md` and follow its instructions from the top with the user's request as input

### Requirement: Upload images to Azure DevOps
The `dobby-ado-close-pbi` skill SHALL upload evidence images to Azure DevOps using the Work Item Tracking Attachments API. The returned attachment URLs SHALL be used to embed images in the markdown comment. This requirement applies only when the active backend is `"ado"`; GitHub-backed projects use a different evidence vehicle (see `github-issue-closing`).

#### Scenario: Successful image upload
- **WHEN** the system uploads an image file to the Attachments API
- **THEN** the API returns a URL that is embedded in the comment as a markdown image reference

#### Scenario: Image exceeds size limit
- **WHEN** the developer provides an image that exceeds the Azure DevOps attachment size limit
- **THEN** the system SHALL warn the developer and skip that image, continuing with remaining evidence

### Requirement: Structured markdown comment format
The closing comment posted by `dobby-ado-close-pbi` SHALL follow a consistent markdown template that includes: a header with the work item ID and title, a "What Changed" section, optional "Before" and "After" image sections, and optional developer notes.

#### Scenario: Comment renders correctly in Azure DevOps
- **WHEN** the closing comment is posted to the work item
- **THEN** the comment SHALL render as formatted markdown in the Azure DevOps discussion thread with visible headings, text, and inline images

### Requirement: Interactive evidence gathering
The `dobby-ado-close-pbi` skill SHALL interactively prompt the developer to provide evidence during the closing flow. The developer SHALL be able to add a text description, attach screenshot files, and optionally add free-form notes.

#### Scenario: Developer is prompted for evidence
- **WHEN** the developer triggers the close action on a work item
- **THEN** the system SHALL prompt for a change description, offer to attach "after" screenshots, check for existing "before" captures, and allow adding developer notes before posting

#### Scenario: Developer cancels closing flow
- **WHEN** the developer cancels during the evidence-gathering prompts
- **THEN** the work item state SHALL NOT change and no comment SHALL be posted

