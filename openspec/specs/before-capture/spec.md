### Requirement: Capture before-state screenshots
The system SHALL provide a command or step that allows the developer to capture "before" screenshots for a work item prior to making changes. These images SHALL be stored locally and associated with the work item ID for later use during the closing flow.

#### Scenario: Developer captures before screenshots
- **WHEN** the developer triggers the before-capture step for a specific work item and provides one or more screenshot files
- **THEN** the system SHALL store the images locally, tagged with the work item ID, so they are available when the closing flow runs

#### Scenario: Before screenshots retrieved at closing time
- **WHEN** the developer initiates the closing flow for a work item that has previously captured before screenshots
- **THEN** the system SHALL automatically include those before screenshots in the closing comment's "Before" section

### Requirement: Before-capture is optional
The before-capture step SHALL be opt-in. The closing flow SHALL NOT require before screenshots to proceed.

#### Scenario: No before screenshots available
- **WHEN** the developer closes a work item without having captured before screenshots
- **THEN** the system SHALL inform the developer that no before images are available and proceed with the closing flow using only "after" evidence

#### Scenario: Prompt about missing before-capture
- **WHEN** the developer initiates the closing flow and no before screenshots exist for the work item
- **THEN** the system SHALL display an informational message noting that before screenshots were not captured, but SHALL NOT block the closing flow

### Requirement: Local storage of before-capture images
The system SHALL store before-capture images in a local directory structure organized by work item ID. The storage location SHALL be deterministic so images can be reliably retrieved during the closing flow.

#### Scenario: Images stored in predictable location
- **WHEN** before screenshots are captured for work item 12345
- **THEN** the images SHALL be stored in a local path that includes the work item ID (e.g., `.dobby/evidence/12345/before/`)

#### Scenario: Multiple before captures for same work item
- **WHEN** the developer captures before screenshots multiple times for the same work item
- **THEN** new captures SHALL be added alongside existing ones without overwriting previous captures
