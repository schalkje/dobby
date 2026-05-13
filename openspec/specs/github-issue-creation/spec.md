# github-issue-creation Specification

## Purpose
TBD - created by archiving change dobby-multi-backend. Update Purpose after archive.
## Requirements
### Requirement: Skill creates a GitHub Issue
The `dobby-gh-create-issue` skill SHALL create a GitHub Issue in the configured repository using the `gh` CLI from a conversational request. The issue body SHALL be markdown-formatted and SHALL contain both the description and the acceptance criteria in a single body, separated by clear headings.

#### Scenario: Successful issue creation with all fields provided
- **WHEN** the user provides a title, description, acceptance criteria, and labels
- **THEN** the skill creates a GitHub Issue with the given title, a markdown body containing a "## Description" section and an "## Acceptance Criteria" section, applies the labels, and reports the issue number and URL

#### Scenario: Successful issue creation with minimal fields
- **WHEN** the user provides only a title
- **THEN** the skill creates a GitHub Issue with the title in the configured repository, prompts for description and acceptance criteria but allows them to be skipped, and reports the issue number and URL

### Requirement: Skill validates prerequisites
The skill SHALL verify that the `gh` CLI is installed and authenticated, and that the configured repository exists and is accessible, before attempting to create an issue.

#### Scenario: gh CLI not installed
- **WHEN** the `gh` command is not available on the system PATH
- **THEN** the skill reports the issue and provides installation instructions without attempting the create operation

#### Scenario: User not authenticated to gh
- **WHEN** `gh auth status` indicates the user is not logged in
- **THEN** the skill prompts the user to run `gh auth login` and does not create the issue

#### Scenario: Repository inaccessible
- **WHEN** the configured `owner/repo` cannot be resolved via `gh repo view`
- **THEN** the skill reports the failure with the resolved repo coordinates and asks the user to correct `.dobby/config.json`

### Requirement: Skill collects connection details on first run
The skill SHALL prompt the user for the GitHub repository coordinates (`owner` and `repo`) on first invocation if they are not present in `.dobby/config.json` under the `github` block, and persist them after a successful issue creation.

#### Scenario: GitHub block missing from config
- **WHEN** the skill runs and `.dobby/config.json` has `backend: "github"` but no `github` block, or the block is missing `owner`/`repo`
- **THEN** the skill SHALL prompt the user for those fields, attempt the create operation, and write the values into `.dobby/config.json` only after the first successful create

#### Scenario: GitHub block present
- **WHEN** the skill runs and the `github` block contains `owner` and `repo`
- **THEN** the skill SHALL use those values without prompting

### Requirement: Skill interactively collects missing fields
The skill SHALL prompt the user for any fields not provided in the initial request, batching prompts where possible.

#### Scenario: Description not specified
- **WHEN** the user does not provide a description
- **THEN** the skill SHALL ask whether to add one and accept either free-text or "skip"

#### Scenario: Acceptance criteria not specified
- **WHEN** the user does not provide acceptance criteria
- **THEN** the skill SHALL ask whether to add Given/When/Then criteria and accept either a list or "skip"

#### Scenario: Labels not specified
- **WHEN** the user does not specify labels and `defaultLabels` is set in `.dobby/config.json`
- **THEN** the skill SHALL apply the default labels without prompting

### Requirement: Skill supports task-list parent linkage
The skill SHALL allow the user to specify a parent issue. The parent linkage SHALL be expressed by appending a task-list reference (`- [ ] #<new-issue-number>`) to the parent issue's body after the new issue is created, since GitHub does not natively support hard parent/child relations on issues outside of Projects.

#### Scenario: Parent issue specified
- **WHEN** the user provides a parent issue number
- **THEN** the skill SHALL create the new issue first, then update the parent issue's body to append a task-list line referencing the new issue, and SHALL report the parent link in the final output

#### Scenario: No parent specified
- **WHEN** the user does not specify a parent
- **THEN** the skill SHALL create the issue without any parent linkage

### Requirement: Skill reports creation result
The skill SHALL display the created issue's number, title, applied labels, parent linkage (if any), and a direct URL to the issue after successful creation.

#### Scenario: Successful creation output
- **WHEN** an issue is successfully created
- **THEN** the skill outputs the issue number (e.g., `#42`), title, labels, parent reference (if any), and a clickable URL

